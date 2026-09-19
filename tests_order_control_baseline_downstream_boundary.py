# Unit tests for downstream boundary observer (design notes 2, pre-implementation spec).
#
# Run from the repository root:
#   python tests_order_control_baseline_downstream_boundary.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import dataclasses
from dataclasses import FrozenInstanceError

from uxsim.order_control_baseline_downstream_boundary import (
    OrderControlBaselineDownstreamBoundaryNodeResult,
    OrderControlBaselineDownstreamBoundaryObserver,
    OrderControlBaselineDownstreamBoundaryOutlinkResult,
    OrderControlBaselineDownstreamBoundaryResult,
)


class _TrapIncomingList(list):
    """Raises if iterated (used to detect unwanted incoming_vehicles access)."""

    def __iter__(self):
        raise AssertionError("incoming_vehicles must not be scanned for this Node")


class FakeNode:
    def __init__(
        self,
        name: str,
        *,
        outlinks: dict | None = None,
        incoming_vehicles: list | None = None,
    ) -> None:
        self.name = name
        self.outlinks = outlinks if outlinks is not None else {}
        self.incoming_vehicles = (
            incoming_vehicles if incoming_vehicles is not None else []
        )


class FakeLink:
    def __init__(
        self,
        name: str,
        *,
        start_node: FakeNode,
        end_node: FakeNode | None,
    ) -> None:
        self.name = name
        self.start_node = start_node
        self.end_node = end_node


class FakeVehicle:
    def __init__(self, name: str, link: FakeLink | None) -> None:
        self.name = name
        self.link = link


def _new_observer() -> OrderControlBaselineDownstreamBoundaryObserver:
    return OrderControlBaselineDownstreamBoundaryObserver()


def _link_chain(
    origin_name: str,
    link_name: str,
    terminal_name: str,
) -> tuple[FakeNode, FakeLink, FakeNode]:
    origin = FakeNode(origin_name)
    terminal = FakeNode(terminal_name)
    link = FakeLink(link_name, start_node=origin, end_node=terminal)
    origin.outlinks = {link_name: link}
    return origin, link, terminal


# --- Result type: normal ---


def test_outlink_result_normal_and_frozen():
    result = OrderControlBaselineDownstreamBoundaryOutlinkResult(
        outlink_name="L1",
        terminal_node_name="B",
        active_timestep_count=0,
        transferred_vehicle_count=0,
    )
    assert result.outlink_name == "L1"
    assert result.terminal_node_name == "B"
    assert result.active_timestep_count == 0
    assert result.transferred_vehicle_count == 0
    try:
        result.outlink_name = "x"
        raise AssertionError("expected FrozenInstanceError")
    except FrozenInstanceError:
        pass


def test_node_result_normal_tuple_hierarchy():
    out = OrderControlBaselineDownstreamBoundaryOutlinkResult(
        outlink_name="L1",
        terminal_node_name="B",
        active_timestep_count=1,
        transferred_vehicle_count=2,
    )
    node_result = OrderControlBaselineDownstreamBoundaryNodeResult(
        node_name="A",
        outlink_results=(out,),
    )
    assert node_result.node_name == "A"
    assert len(node_result.outlink_results) == 1
    assert node_result.outlink_results[0] is out


def test_overall_result_normal():
    out = OrderControlBaselineDownstreamBoundaryOutlinkResult(
        outlink_name="L1",
        terminal_node_name="B",
        active_timestep_count=0,
        transferred_vehicle_count=0,
    )
    node_result = OrderControlBaselineDownstreamBoundaryNodeResult(
        node_name="A",
        outlink_results=(out,),
    )
    overall = OrderControlBaselineDownstreamBoundaryResult(
        node_results=(node_result,),
    )
    assert overall.node_results[0] is node_result


# --- Result type: validation errors ---


def test_outlink_result_rejects_empty_outlink_name():
    try:
        OrderControlBaselineDownstreamBoundaryOutlinkResult(
            outlink_name="",
            terminal_node_name="B",
            active_timestep_count=0,
            transferred_vehicle_count=0,
        )
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "outlink_name" in str(error)


def test_outlink_result_rejects_empty_terminal_node_name():
    try:
        OrderControlBaselineDownstreamBoundaryOutlinkResult(
            outlink_name="L1",
            terminal_node_name="",
            active_timestep_count=0,
            transferred_vehicle_count=0,
        )
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "terminal_node_name" in str(error)


def test_node_result_rejects_empty_node_name():
    out = OrderControlBaselineDownstreamBoundaryOutlinkResult(
        outlink_name="L1",
        terminal_node_name="B",
        active_timestep_count=0,
        transferred_vehicle_count=0,
    )
    try:
        OrderControlBaselineDownstreamBoundaryNodeResult(
            node_name="",
            outlink_results=(out,),
        )
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "node_name" in str(error)


def test_outlink_result_rejects_negative_active_count():
    try:
        OrderControlBaselineDownstreamBoundaryOutlinkResult(
            outlink_name="L1",
            terminal_node_name="B",
            active_timestep_count=-1,
            transferred_vehicle_count=0,
        )
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "active_timestep_count" in str(error)


def test_outlink_result_rejects_bool_active_count():
    try:
        OrderControlBaselineDownstreamBoundaryOutlinkResult(
            outlink_name="L1",
            terminal_node_name="B",
            active_timestep_count=True,
            transferred_vehicle_count=0,
        )
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "active_timestep_count" in str(error)


def test_outlink_result_rejects_float_transferred_count():
    try:
        OrderControlBaselineDownstreamBoundaryOutlinkResult(
            outlink_name="L1",
            terminal_node_name="B",
            active_timestep_count=0,
            transferred_vehicle_count=1.5,
        )
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "transferred_vehicle_count" in str(error)


def test_node_result_rejects_non_tuple_outlink_results():
    out = OrderControlBaselineDownstreamBoundaryOutlinkResult(
        outlink_name="L1",
        terminal_node_name="B",
        active_timestep_count=0,
        transferred_vehicle_count=0,
    )
    try:
        OrderControlBaselineDownstreamBoundaryNodeResult(
            node_name="A",
            outlink_results=[out],
        )
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "outlink_results" in str(error)


def test_node_result_rejects_wrong_element_type_in_outlink_results():
    try:
        OrderControlBaselineDownstreamBoundaryNodeResult(
            node_name="A",
            outlink_results=("not-a-result",),
        )
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "outlink_results[0]" in str(error)


def test_overall_result_rejects_non_tuple_node_results():
    node_result = OrderControlBaselineDownstreamBoundaryNodeResult(
        node_name="A",
        outlink_results=(),
    )
    try:
        OrderControlBaselineDownstreamBoundaryResult(node_results=[node_result])
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "node_results" in str(error)


def test_overall_result_rejects_wrong_element_type_in_node_results():
    try:
        OrderControlBaselineDownstreamBoundaryResult(node_results=("bad",))
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "node_results[0]" in str(error)


# --- Registration: single target, single outlink ---


def test_register_single_target_single_outlink_export_fields():
    observer = _new_observer()
    origin, link, terminal = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    result = observer.export_result()
    assert len(result.node_results) == 1
    node_result = result.node_results[0]
    assert node_result.node_name == "A"
    assert len(node_result.outlink_results) == 1
    out_result = node_result.outlink_results[0]
    assert out_result.outlink_name == "A_to_B"
    assert out_result.terminal_node_name == "B"
    assert out_result.active_timestep_count == 0
    assert out_result.transferred_vehicle_count == 0


# --- Multiple outlinks on one target ---


def test_multiple_outlinks_preserve_outlink_registration_order():
    observer = _new_observer()
    origin = FakeNode("A")
    terminal_b = FakeNode("B")
    terminal_c = FakeNode("C")
    link_ab = FakeLink("A_to_B", start_node=origin, end_node=terminal_b)
    link_ac = FakeLink("A_to_C", start_node=origin, end_node=terminal_c)
    origin.outlinks = {"A_to_B": link_ab, "A_to_C": link_ac}
    observer.register_target_node_outlinks(origin)
    names = [
        o.outlink_name
        for o in observer.export_result().node_results[0].outlink_results
    ]
    assert names == ["A_to_B", "A_to_C"]


# --- Multiple target Nodes ---


def test_multiple_target_nodes_preserve_registration_order():
    observer = _new_observer()
    a, _, _ = _link_chain("A", "A_to_B", "B")
    d, _, _ = _link_chain("D", "D_to_E", "E")
    observer.register_target_node_outlinks(a)
    observer.register_target_node_outlinks(d)
    node_names = [n.node_name for n in observer.export_result().node_results]
    assert node_names == ["A", "D"]


# --- Shared terminal Node ---


def test_shared_terminal_node_separate_outlink_results():
    observer = _new_observer()
    a, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    d = FakeNode("D")
    link_db = FakeLink("D_to_B", start_node=d, end_node=terminal_b)
    d.outlinks = {"D_to_B": link_db}
    observer.register_target_node_outlinks(a)
    observer.register_target_node_outlinks(d)
    exported = observer.export_result()
    assert exported.node_results[0].outlink_results[0].outlink_name == "A_to_B"
    assert exported.node_results[1].outlink_results[0].outlink_name == "D_to_B"
    assert (
        exported.node_results[0].outlink_results[0].terminal_node_name
        == exported.node_results[1].outlink_results[0].terminal_node_name
    )


def test_shared_terminal_capture_commit_separate_by_vehicle_link():
    observer = _new_observer()
    a, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    d = FakeNode("D")
    link_db = FakeLink("D_to_B", start_node=d, end_node=terminal_b)
    d.outlinks = {"D_to_B": link_db}
    observer.register_target_node_outlinks(a)
    observer.register_target_node_outlinks(d)

    veh_ab = FakeVehicle("v_ab", link_ab)
    veh_db = FakeVehicle("v_db", link_db)
    other_link = FakeLink("other", start_node=terminal_b, end_node=FakeNode("Z"))
    terminal_b.incoming_vehicles = [veh_ab, veh_db]

    observer.capture_before_transfer(terminal_b)
    veh_ab.link = other_link
    veh_db.link = link_db
    observer.commit_after_transfer(terminal_b)

    exported = observer.export_result()
    a_out = exported.node_results[0].outlink_results[0]
    d_out = exported.node_results[1].outlink_results[0]
    assert a_out.active_timestep_count == 1
    assert a_out.transferred_vehicle_count == 1
    assert d_out.active_timestep_count == 1
    assert d_out.transferred_vehicle_count == 0


# --- Duplicate registration ---


def test_duplicate_target_node_registration_raises():
    observer = _new_observer()
    origin, _, _ = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    try:
        observer.register_target_node_outlinks(origin)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "A" in str(error)


def test_duplicate_outlink_object_registration_raises():
    observer = _new_observer()
    origin, link, terminal = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    other = FakeNode("D")
    other.outlinks = {"A_to_B": link}
    try:
        observer.register_target_node_outlinks(other)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "A_to_B" in str(error)


def test_duplicate_outlink_within_same_target_registration_raises_atomically():
    observer = _new_observer()
    origin = FakeNode("A")
    terminal = FakeNode("B")
    same_outlink = FakeLink("A_to_B", start_node=origin, end_node=terminal)
    origin.outlinks = {
        "first_key": same_outlink,
        "second_key": same_outlink,
    }
    try:
        observer.register_target_node_outlinks(origin)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        message = str(error)
        assert "A" in message
        assert "A_to_B" in message
    exported = observer.export_result()
    assert exported.node_results == ()
    assert len(observer._target_node_states) == 0


def test_duplicate_outlink_failure_does_not_corrupt_prior_registration():
    observer = _new_observer()
    origin, link, _ = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    other = FakeNode("D")
    other.outlinks = {"A_to_B": link}
    try:
        observer.register_target_node_outlinks(other)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    exported = observer.export_result()
    assert len(exported.node_results) == 1
    assert exported.node_results[0].node_name == "A"


# --- Outlink integrity ---


def test_register_rejects_wrong_start_node():
    observer = _new_observer()
    origin = FakeNode("A")
    terminal = FakeNode("B")
    wrong_start = FakeNode("X")
    link = FakeLink("A_to_B", start_node=wrong_start, end_node=terminal)
    origin.outlinks = {"A_to_B": link}
    try:
        observer.register_target_node_outlinks(origin)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "A_to_B" in str(error)


def test_register_rejects_missing_end_node():
    observer = _new_observer()
    origin = FakeNode("A")
    link = FakeLink("A_to_B", start_node=origin, end_node=None)
    origin.outlinks = {"A_to_B": link}
    try:
        observer.register_target_node_outlinks(origin)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "end_node" in str(error)


def test_register_rejects_empty_outlink_name():
    observer = _new_observer()
    origin, _, terminal = _link_chain("A", "", "B")
    try:
        observer.register_target_node_outlinks(origin)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "outlink.name" in str(error)


def test_register_rejects_zero_outlinks_on_target_node():
    observer = _new_observer()
    origin = FakeNode("A")
    origin.outlinks = {}
    try:
        observer.register_target_node_outlinks(origin)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "A" in str(error)


# --- Non-target terminal capture ---


def test_capture_on_unregistered_terminal_is_no_op():
    observer = _new_observer()
    origin, _, _ = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    unrelated = FakeNode("Z", incoming_vehicles=_TrapIncomingList())
    created = observer.capture_before_transfer(unrelated)
    assert created is False
    assert observer._pending_capture is None
    exported = observer.export_result()
    assert exported.node_results[0].outlink_results[0].active_timestep_count == 0


# --- Capture behavior ---


def test_capture_keeps_only_vehicles_on_monitored_outlink():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    other_inlink = FakeLink("other_in", start_node=FakeNode("U"), end_node=terminal_b)
    veh_match = FakeVehicle("match", link_ab)
    veh_other = FakeVehicle("other", other_inlink)
    terminal_b.incoming_vehicles = [veh_match, veh_other]
    observer.capture_before_transfer(terminal_b)
    pending = observer._pending_capture
    assert pending is not None
    snapshots = pending.outlink_vehicle_snapshots
    assert len(snapshots) == 1
    _, captured = snapshots[0]
    assert captured == (veh_match,)


def test_capture_multiple_vehicles_same_outlink():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    v1 = FakeVehicle("v1", link_ab)
    v2 = FakeVehicle("v2", link_ab)
    terminal_b.incoming_vehicles = [v1, v2]
    observer.capture_before_transfer(terminal_b)
    _, captured = observer._pending_capture.outlink_vehicle_snapshots[0]
    assert captured == (v1, v2)


def test_capture_does_not_change_committed_counts():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    terminal_b.incoming_vehicles = [FakeVehicle("v1", link_ab)]
    observer.capture_before_transfer(terminal_b)
    outlink_state = observer._target_node_states[0].outlink_states[0]
    assert outlink_state.active_timestep_count == 0
    assert outlink_state.transferred_vehicle_count == 0
    observer.clear_pending()


def test_capture_returns_true_for_monitored_terminal():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    terminal_b.incoming_vehicles = [FakeVehicle("v1", link_ab)]
    created = observer.capture_before_transfer(terminal_b)
    assert created is True
    assert observer._pending_capture is not None
    observer.clear_pending()


def test_capture_returns_true_for_monitored_terminal_with_no_vehicles():
    observer = _new_observer()
    origin, _, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    terminal_b.incoming_vehicles = []
    created = observer.capture_before_transfer(terminal_b)
    assert created is True
    assert observer._pending_capture is not None
    observer.commit_after_transfer(terminal_b)
    out = observer.export_result().node_results[0].outlink_results[0]
    assert out.active_timestep_count == 0
    assert out.transferred_vehicle_count == 0


def test_capture_exception_during_vehicle_scan_leaves_no_pending():
    observer = _new_observer()
    origin, _, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)

    class _RaisingLinkVehicle:
        @property
        def link(self):
            raise RuntimeError("vehicle.link access failed")

    terminal_b.incoming_vehicles = [_RaisingLinkVehicle()]
    try:
        observer.capture_before_transfer(terminal_b)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert str(error) == "vehicle.link access failed"
    assert observer._pending_capture is None


def test_double_capture_raises_runtime_error():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    terminal_b.incoming_vehicles = [FakeVehicle("v1", link_ab)]
    observer.capture_before_transfer(terminal_b)
    try:
        observer.capture_before_transfer(terminal_b)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert "pending" in str(error).lower()


# --- Commit behavior ---


def test_commit_vehicle_stays_on_outlink_zero_transfer():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    veh = FakeVehicle("v1", link_ab)
    terminal_b.incoming_vehicles = [veh]
    observer.capture_before_transfer(terminal_b)
    observer.commit_after_transfer(terminal_b)
    out = observer.export_result().node_results[0].outlink_results[0]
    assert out.active_timestep_count == 1
    assert out.transferred_vehicle_count == 0


def test_commit_vehicle_moves_to_other_link_counts_transfer():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    veh = FakeVehicle("v1", link_ab)
    terminal_b.incoming_vehicles = [veh]
    observer.capture_before_transfer(terminal_b)
    next_link = FakeLink("B_to_C", start_node=terminal_b, end_node=FakeNode("C"))
    veh.link = next_link
    observer.commit_after_transfer(terminal_b)
    out = observer.export_result().node_results[0].outlink_results[0]
    assert out.transferred_vehicle_count == 1


def test_commit_multiple_transfers_count_all():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    v1 = FakeVehicle("v1", link_ab)
    v2 = FakeVehicle("v2", link_ab)
    terminal_b.incoming_vehicles = [v1, v2]
    observer.capture_before_transfer(terminal_b)
    next_link = FakeLink("B_to_C", start_node=terminal_b, end_node=FakeNode("C"))
    v1.link = next_link
    v2.link = next_link
    observer.commit_after_transfer(terminal_b)
    out = observer.export_result().node_results[0].outlink_results[0]
    assert out.transferred_vehicle_count == 2


def test_commit_partial_transfer_counts_only_moved():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    v1 = FakeVehicle("v1", link_ab)
    v2 = FakeVehicle("v2", link_ab)
    terminal_b.incoming_vehicles = [v1, v2]
    observer.capture_before_transfer(terminal_b)
    next_link = FakeLink("B_to_C", start_node=terminal_b, end_node=FakeNode("C"))
    v1.link = next_link
    v2.link = link_ab
    observer.commit_after_transfer(terminal_b)
    out = observer.export_result().node_results[0].outlink_results[0]
    assert out.transferred_vehicle_count == 1


def test_commit_link_none_does_not_count_transfer():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    veh = FakeVehicle("v1", link_ab)
    terminal_b.incoming_vehicles = [veh]
    observer.capture_before_transfer(terminal_b)
    veh.link = None
    observer.commit_after_transfer(terminal_b)
    out = observer.export_result().node_results[0].outlink_results[0]
    assert out.active_timestep_count == 1
    assert out.transferred_vehicle_count == 0


def test_commit_active_count_one_per_outlink_per_timestep_even_with_many_vehicles():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    terminal_b.incoming_vehicles = [
        FakeVehicle("v1", link_ab),
        FakeVehicle("v2", link_ab),
    ]
    observer.capture_before_transfer(terminal_b)
    observer.commit_after_transfer(terminal_b)
    out = observer.export_result().node_results[0].outlink_results[0]
    assert out.active_timestep_count == 1


def test_commit_wrong_node_raises_runtime_error():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    terminal_b.incoming_vehicles = [FakeVehicle("v1", link_ab)]
    observer.capture_before_transfer(terminal_b)
    wrong = FakeNode("wrong")
    try:
        observer.commit_after_transfer(wrong)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert "capture" in str(error).lower()


def test_commit_without_pending_raises_runtime_error():
    observer = _new_observer()
    origin, _, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    try:
        observer.commit_after_transfer(terminal_b)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert "pending" in str(error).lower()


def test_commit_clears_pending_and_clear_pending_is_safe_no_op():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    terminal_b.incoming_vehicles = [FakeVehicle("v1", link_ab)]
    observer.capture_before_transfer(terminal_b)
    observer.commit_after_transfer(terminal_b)
    assert observer._pending_capture is None
    observer.clear_pending()
    assert observer._pending_capture is None


# --- Multiple timesteps ---


def test_multiple_timesteps_accumulate_counts():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    next_link = FakeLink("B_to_C", start_node=terminal_b, end_node=FakeNode("C"))

    for _ in range(3):
        veh = FakeVehicle("v", link_ab)
        terminal_b.incoming_vehicles = [veh]
        observer.capture_before_transfer(terminal_b)
        veh.link = next_link
        observer.commit_after_transfer(terminal_b)

    out = observer.export_result().node_results[0].outlink_results[0]
    assert out.active_timestep_count == 3
    assert out.transferred_vehicle_count == 3


# --- clear_pending ---


def test_clear_pending_after_capture_discards_without_counting():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    terminal_b.incoming_vehicles = [FakeVehicle("v1", link_ab)]
    observer.capture_before_transfer(terminal_b)
    observer.clear_pending()
    out = observer.export_result().node_results[0].outlink_results[0]
    assert out.active_timestep_count == 0
    assert out.transferred_vehicle_count == 0


def test_clear_pending_preserves_prior_committed_counts():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    next_link = FakeLink("B_to_C", start_node=terminal_b, end_node=FakeNode("C"))
    veh = FakeVehicle("v1", link_ab)
    terminal_b.incoming_vehicles = [veh]
    observer.capture_before_transfer(terminal_b)
    veh.link = next_link
    observer.commit_after_transfer(terminal_b)

    terminal_b.incoming_vehicles = [FakeVehicle("v2", link_ab)]
    observer.capture_before_transfer(terminal_b)
    observer.clear_pending()

    out = observer.export_result().node_results[0].outlink_results[0]
    assert out.active_timestep_count == 1
    assert out.transferred_vehicle_count == 1


def test_clear_pending_allows_next_capture():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    terminal_b.incoming_vehicles = [FakeVehicle("v1", link_ab)]
    observer.capture_before_transfer(terminal_b)
    observer.clear_pending()
    observer.capture_before_transfer(terminal_b)
    observer.clear_pending()


# --- export ---


def test_export_with_pending_raises_runtime_error():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    terminal_b.incoming_vehicles = [FakeVehicle("v1", link_ab)]
    observer.capture_before_transfer(terminal_b)
    try:
        observer.export_result()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert "pending" in str(error).lower()


def test_export_result_has_no_average_or_horizon_fields():
    observer = _new_observer()
    origin, _, _ = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    result = observer.export_result()
    forbidden = (
        "average",
        "horizon",
        "configured",
        "rate",
    )
    for dataclass_type in (
        OrderControlBaselineDownstreamBoundaryResult,
        OrderControlBaselineDownstreamBoundaryNodeResult,
        OrderControlBaselineDownstreamBoundaryOutlinkResult,
    ):
        for field_info in dataclasses.fields(dataclass_type):
            lowered = field_info.name.lower()
            for token in forbidden:
                assert token not in lowered


def test_export_multiple_times_independent_and_prior_unchanged():
    observer = _new_observer()
    origin, link_ab, terminal_b = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    first = observer.export_result()

    terminal_b.incoming_vehicles = [FakeVehicle("v1", link_ab)]
    observer.capture_before_transfer(terminal_b)
    observer.commit_after_transfer(terminal_b)

    second = observer.export_result()
    assert first.node_results[0].outlink_results[0].active_timestep_count == 0
    assert second.node_results[0].outlink_results[0].active_timestep_count == 1
    assert first is not second


def test_export_does_not_store_object_references_in_result():
    observer = _new_observer()
    origin, _, _ = _link_chain("A", "A_to_B", "B")
    observer.register_target_node_outlinks(origin)
    result = observer.export_result()
    for node_result in result.node_results:
        assert isinstance(node_result.node_name, str)
        for out_result in node_result.outlink_results:
            assert isinstance(out_result.outlink_name, str)
            assert isinstance(out_result.terminal_node_name, str)


def test_tests_list_registration():
    assert len(TESTS) >= 1
    assert test_register_single_target_single_outlink_export_fields in TESTS


TESTS = [
    test_outlink_result_normal_and_frozen,
    test_node_result_normal_tuple_hierarchy,
    test_overall_result_normal,
    test_outlink_result_rejects_empty_outlink_name,
    test_outlink_result_rejects_empty_terminal_node_name,
    test_node_result_rejects_empty_node_name,
    test_outlink_result_rejects_negative_active_count,
    test_outlink_result_rejects_bool_active_count,
    test_outlink_result_rejects_float_transferred_count,
    test_node_result_rejects_non_tuple_outlink_results,
    test_node_result_rejects_wrong_element_type_in_outlink_results,
    test_overall_result_rejects_non_tuple_node_results,
    test_overall_result_rejects_wrong_element_type_in_node_results,
    test_register_single_target_single_outlink_export_fields,
    test_multiple_outlinks_preserve_outlink_registration_order,
    test_multiple_target_nodes_preserve_registration_order,
    test_shared_terminal_node_separate_outlink_results,
    test_shared_terminal_capture_commit_separate_by_vehicle_link,
    test_duplicate_target_node_registration_raises,
    test_duplicate_outlink_object_registration_raises,
    test_duplicate_outlink_within_same_target_registration_raises_atomically,
    test_duplicate_outlink_failure_does_not_corrupt_prior_registration,
    test_register_rejects_wrong_start_node,
    test_register_rejects_missing_end_node,
    test_register_rejects_empty_outlink_name,
    test_register_rejects_zero_outlinks_on_target_node,
    test_capture_on_unregistered_terminal_is_no_op,
    test_capture_keeps_only_vehicles_on_monitored_outlink,
    test_capture_multiple_vehicles_same_outlink,
    test_capture_does_not_change_committed_counts,
    test_capture_returns_true_for_monitored_terminal,
    test_capture_returns_true_for_monitored_terminal_with_no_vehicles,
    test_capture_exception_during_vehicle_scan_leaves_no_pending,
    test_double_capture_raises_runtime_error,
    test_commit_vehicle_stays_on_outlink_zero_transfer,
    test_commit_vehicle_moves_to_other_link_counts_transfer,
    test_commit_multiple_transfers_count_all,
    test_commit_partial_transfer_counts_only_moved,
    test_commit_link_none_does_not_count_transfer,
    test_commit_active_count_one_per_outlink_per_timestep_even_with_many_vehicles,
    test_commit_wrong_node_raises_runtime_error,
    test_commit_without_pending_raises_runtime_error,
    test_commit_clears_pending_and_clear_pending_is_safe_no_op,
    test_multiple_timesteps_accumulate_counts,
    test_clear_pending_after_capture_discards_without_counting,
    test_clear_pending_preserves_prior_committed_counts,
    test_clear_pending_allows_next_capture,
    test_export_with_pending_raises_runtime_error,
    test_export_result_has_no_average_or_horizon_fields,
    test_export_multiple_times_independent_and_prior_unchanged,
    test_export_does_not_store_object_references_in_result,
    test_tests_list_registration,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print(
        "Order-control baseline downstream boundary tests passed "
        f"({len(TESTS)} tests)."
    )
