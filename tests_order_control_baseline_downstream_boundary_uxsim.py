# UXsim connection tests for the downstream boundary observer exec_simulation hook.
#
# Run from the repository root:
#   python tests_order_control_baseline_downstream_boundary_uxsim.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

from __future__ import annotations

import pickle
from pathlib import Path
from types import MethodType

from uxsim import World
from uxsim.order_control_baseline_downstream_boundary import (
    OrderControlBaselineDownstreamBoundaryObserver,
)

_UXSIM_SOURCE_PATH = Path(__file__).resolve().parent / "uxsim" / "uxsim.py"


def _build_world(name: str, *, tmax: int = 40):
    return World(
        name=name,
        deltan=1,
        tmax=tmax,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=0,
    )


def _build_merge_network(W):
    W.addNode("orig1", 0, 1)
    W.addNode("orig2", 0, -1)
    merge = W.addNode("merge", 1, 0)
    dest = W.addNode("dest", 2, 0)
    W.addLink(
        "in1",
        "orig1",
        "merge",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    W.addLink(
        "in2",
        "orig2",
        "merge",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    W.addLink(
        "out",
        "merge",
        "dest",
        length=100,
        free_flow_speed=20,
        number_of_lanes=1,
    )
    W.infer_order_control_eligible_nodes()
    return merge, dest


def _rng_state_bytes(rng) -> bytes:
    return pickle.dumps(rng.bit_generator.state)


def _wrap_transfers(W, recorded: list[tuple[str, str]]) -> None:
    for node in W.NODES:
        original_transfer = node.transfer

        def wrapped(_self, orig=original_transfer, n=node):
            recorded.append(("transfer", n.name))
            return orig()

        node.transfer = MethodType(wrapped, node)


class _SpyObserver:
    def __init__(
        self,
        inner: OrderControlBaselineDownstreamBoundaryObserver | None = None,
        *,
        capture_result: bool | None = None,
    ) -> None:
        self.inner = inner
        self.capture_result = capture_result
        self.calls: list[tuple[str, str]] = []

    def capture_before_transfer(self, node) -> bool:
        self.calls.append(("capture", node.name))
        if self.inner is not None:
            return self.inner.capture_before_transfer(node)
        if self.capture_result is not None:
            return self.capture_result
        return False

    def commit_after_transfer(self, node) -> None:
        self.calls.append(("commit", node.name))
        if self.inner is not None:
            self.inner.commit_after_transfer(node)

    def clear_pending(self) -> None:
        self.calls.append(("clear", ""))
        if self.inner is not None:
            self.inner.clear_pending()


class _CaptureRaisingObserver:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def capture_before_transfer(self, node) -> bool:
        self.calls.append("capture")
        raise RuntimeError("spy capture failure")

    def commit_after_transfer(self, node) -> None:
        self.calls.append("commit")
        raise AssertionError("commit must not be called")

    def clear_pending(self) -> None:
        self.calls.append("clear")
        raise AssertionError("clear must not be called")


class _CommitRaisingObserver:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def capture_before_transfer(self, node) -> bool:
        self.calls.append("capture")
        return True

    def commit_after_transfer(self, node) -> None:
        self.calls.append("commit")
        raise RuntimeError("spy commit failure")

    def clear_pending(self) -> None:
        self.calls.append("clear")


def _run_one_timestep(W) -> None:
    W.finalize_scenario()
    W.exec_simulation(duration_t2=W.DELTAT)


def test_world_observer_attribute_defaults_none():
    W = _build_world("observer_attr_default")
    assert W._order_control_baseline_downstream_boundary_observer is None
    assert W._order_control_baseline_collector is None


def test_world_copy_keeps_none_observer():
    W = _build_world("observer_copy_none")
    fork_W = W.copy()
    assert W._order_control_baseline_downstream_boundary_observer is None
    assert fork_W._order_control_baseline_downstream_boundary_observer is None


def test_manual_observer_attachment_preserved():
    W = _build_world("observer_manual_attach")
    observer = OrderControlBaselineDownstreamBoundaryObserver()
    W._order_control_baseline_downstream_boundary_observer = observer
    assert W._order_control_baseline_downstream_boundary_observer is observer


def test_observer_attribute_does_not_change_baseline_collector():
    W = _build_world("observer_collector_independent")
    collector_marker = object()
    W._order_control_baseline_collector = collector_marker
    observer = OrderControlBaselineDownstreamBoundaryObserver()
    W._order_control_baseline_downstream_boundary_observer = observer
    assert W._order_control_baseline_collector is collector_marker
    assert W._order_control_baseline_downstream_boundary_observer is observer


def test_exec_simulation_without_observer_calls_transfer_in_node_order():
    W = _build_world("no_observer_transfer_order")
    _build_merge_network(W)
    recorded: list[tuple[str, str]] = []
    _wrap_transfers(W, recorded)
    _run_one_timestep(W)
    expected = [("transfer", node.name) for node in W.NODES]
    assert recorded == expected


def test_two_worlds_without_observer_match_rng_and_results():
    W1 = _build_world("rng_a", tmax=30)
    W2 = _build_world("rng_b", tmax=30)
    _build_merge_network(W1)
    _build_merge_network(W2)
    W1.adddemand("orig1", "dest", 0, 20, 0.2)
    W2.adddemand("orig1", "dest", 0, 20, 0.2)
    W1._order_control_baseline_downstream_boundary_observer = None
    assert W2._order_control_baseline_downstream_boundary_observer is None
    W1.exec_simulation()
    W2.exec_simulation()
    assert _rng_state_bytes(W1.rng) == _rng_state_bytes(W2.rng)
    assert _rng_state_bytes(W1.order_control_rng) == _rng_state_bytes(
        W2.order_control_rng
    )
    names = sorted(W1.VEHICLES.keys())
    assert names == sorted(W2.VEHICLES.keys())
    for name in names:
        assert W1.VEHICLES[name].state == W2.VEHICLES[name].state


def test_non_terminal_node_capture_false_without_commit_or_clear():
    W = _build_world("non_terminal_no_commit")
    merge, _dest = _build_merge_network(W)
    inner = OrderControlBaselineDownstreamBoundaryObserver()
    inner.register_target_node_outlinks(merge)
    spy = _SpyObserver(inner=inner)
    W._order_control_baseline_downstream_boundary_observer = spy
    _run_one_timestep(W)
    orig_calls = [call for call in spy.calls if call[1] == "orig1"]
    assert orig_calls == [("capture", "orig1")]
    assert ("commit", "orig1") not in spy.calls
    assert inner.export_result().node_results[0].outlink_results[0].active_timestep_count == 0


def test_monitored_terminal_call_order_is_capture_transfer_commit_clear():
    W = _build_world("terminal_call_order")
    merge, dest = _build_merge_network(W)
    inner = OrderControlBaselineDownstreamBoundaryObserver()
    inner.register_target_node_outlinks(merge)
    spy = _SpyObserver(inner=inner)
    W._order_control_baseline_downstream_boundary_observer = spy
    original_transfer = dest.transfer

    def recording_transfer(_self):
        spy.calls.append(("transfer", dest.name))
        return original_transfer()

    dest.transfer = MethodType(recording_transfer, dest)
    _run_one_timestep(W)

    dest_span: list[str] = []
    for kind, name in spy.calls:
        if kind == "capture" and name == "dest":
            dest_span = ["capture"]
        elif dest_span == ["capture"] and kind == "transfer" and name == "dest":
            dest_span.append("transfer")
        elif dest_span == ["capture", "transfer"] and kind == "commit" and name == "dest":
            dest_span.append("commit")
        elif dest_span == ["capture", "transfer", "commit"] and kind == "clear":
            dest_span.append("clear")
            break
    assert dest_span == ["capture", "transfer", "commit", "clear"]

    orig_events = [call[0] for call in spy.calls if call[1] == "orig1"]
    assert orig_events == ["capture"]


def test_real_observer_counts_through_exec_simulation():
    W = _build_world("real_observer_exec", tmax=40)
    _merge, _dest = _build_merge_network(W)
    orig1 = W.get_node("orig1")
    observer = OrderControlBaselineDownstreamBoundaryObserver()
    observer.register_target_node_outlinks(orig1)
    W._order_control_baseline_downstream_boundary_observer = observer
    W.adddemand("orig1", "dest", 0, 20, 0.4)
    W.exec_simulation()
    result = observer.export_result()
    out_result = result.node_results[0].outlink_results[0]
    assert out_result.outlink_name == "in1"
    assert out_result.terminal_node_name == "merge"
    assert out_result.active_timestep_count >= 1
    assert out_result.transferred_vehicle_count >= 1
    assert observer._pending_capture is None


def test_transfer_exception_on_monitored_terminal_clears_without_commit():
    W = _build_world("terminal_transfer_error")
    merge, dest = _build_merge_network(W)
    inner = OrderControlBaselineDownstreamBoundaryObserver()
    inner.register_target_node_outlinks(merge)
    spy = _SpyObserver(inner=inner)
    W._order_control_baseline_downstream_boundary_observer = spy
    later_transfers: list[str] = []
    dest_index = W.NODES.index(dest)
    for node in W.NODES[dest_index + 1 :]:
        original = node.transfer

        def wrapped(_self, orig=original, n=node):
            later_transfers.append(n.name)
            return orig()

        node.transfer = MethodType(wrapped, node)

    def failing_transfer(_self):
        raise ValueError("transfer failed for test")

    dest.transfer = MethodType(failing_transfer, dest)

    try:
        _run_one_timestep(W)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert str(error) == "transfer failed for test"

    assert ("commit", "dest") not in spy.calls
    assert ("clear", "") in spy.calls
    assert later_transfers == []
    inner.export_result()


def test_transfer_exception_on_non_terminal_does_not_commit_or_clear():
    W = _build_world("non_terminal_transfer_error")
    merge, _dest = _build_merge_network(W)
    inner = OrderControlBaselineDownstreamBoundaryObserver()
    inner.register_target_node_outlinks(merge)
    spy = _SpyObserver(inner=inner)
    W._order_control_baseline_downstream_boundary_observer = spy
    orig1 = W.get_node("orig1")
    later_transfers: list[str] = []
    orig_index = W.NODES.index(orig1)
    for node in W.NODES[orig_index + 1 :]:
        original = node.transfer

        def wrapped(_self, orig=original, n=node):
            later_transfers.append(n.name)
            return orig()

        node.transfer = MethodType(wrapped, node)

    def failing_transfer(_self):
        raise ValueError("orig1 transfer failed")

    orig1.transfer = MethodType(failing_transfer, orig1)

    try:
        _run_one_timestep(W)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert str(error) == "orig1 transfer failed"
    assert spy.calls == [("capture", "orig1")]
    assert later_transfers == []


def test_capture_exception_does_not_call_transfer_commit_or_clear():
    W = _build_world("capture_exception")
    _build_merge_network(W)
    spy = _CaptureRaisingObserver()
    W._order_control_baseline_downstream_boundary_observer = spy
    transfer_called = False
    for node in W.NODES:
        original = node.transfer

        def wrapped(_self, orig=original):
            nonlocal transfer_called
            transfer_called = True
            return orig()

        node.transfer = MethodType(wrapped, node)
    try:
        _run_one_timestep(W)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert str(error) == "spy capture failure"
    assert transfer_called is False
    assert spy.calls == ["capture"]


def test_commit_exception_still_clears_pending():
    W = _build_world("commit_exception")
    _build_merge_network(W)
    spy = _CommitRaisingObserver()
    W._order_control_baseline_downstream_boundary_observer = spy
    try:
        _run_one_timestep(W)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert str(error) == "spy commit failure"
    assert spy.calls == ["capture", "commit", "clear"]


def test_fcfs_merge_uses_common_hook_without_observer():
    W = _build_world("fcfs_hook_path")
    merge, _dest = _build_merge_network(W)
    W.set_order_control_for_nodes(["merge"], order_control_type="fcfs")
    assert merge.order_control_type == "fcfs"
    assert W._order_control_baseline_downstream_boundary_observer is None
    _run_one_timestep(W)


def test_batch_merge_uses_common_hook_without_observer():
    W = _build_world("batch_hook_path")
    merge, _dest = _build_merge_network(W)
    W.set_order_control_for_nodes(
        ["merge"],
        order_control_type="batch",
        batch_size=2,
    )
    assert merge.order_control_type == "batch"
    _run_one_timestep(W)


def test_uxsim_hook_does_not_use_private_state_or_export_pending_detection():
    source_text = _UXSIM_SOURCE_PATH.read_text(encoding="utf-8")
    forbidden = (
        "_pending_capture",
        "_outlink_states_by_terminal_node_id",
        "_target_node_states",
        "_order_control_baseline_downstream_boundary_capture_is_pending",
    )
    for token in forbidden:
        assert token not in source_text
    exec_start = source_text.index("def exec_simulation(")
    exec_end = source_text.index("\n    def ", exec_start + 1)
    exec_source = source_text[exec_start:exec_end]
    assert "export_result" not in exec_source
    assert "type<class" not in exec_source


TESTS = [
    test_world_observer_attribute_defaults_none,
    test_world_copy_keeps_none_observer,
    test_manual_observer_attachment_preserved,
    test_observer_attribute_does_not_change_baseline_collector,
    test_exec_simulation_without_observer_calls_transfer_in_node_order,
    test_two_worlds_without_observer_match_rng_and_results,
    test_non_terminal_node_capture_false_without_commit_or_clear,
    test_monitored_terminal_call_order_is_capture_transfer_commit_clear,
    test_real_observer_counts_through_exec_simulation,
    test_transfer_exception_on_monitored_terminal_clears_without_commit,
    test_transfer_exception_on_non_terminal_does_not_commit_or_clear,
    test_capture_exception_does_not_call_transfer_commit_or_clear,
    test_commit_exception_still_clears_pending,
    test_fcfs_merge_uses_common_hook_without_observer,
    test_batch_merge_uses_common_hook_without_observer,
    test_uxsim_hook_does_not_use_private_state_or_export_pending_detection,
]


if __name__ == "__main__":
    for test_func in TESTS:
        test_func()
    print(
        "Order-control baseline downstream boundary UXsim hook tests passed "
        f"({len(TESTS)} tests)."
    )
