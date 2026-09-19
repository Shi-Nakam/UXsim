"""
Downstream boundary observation for all-World baseline (outlink terminal).

Registers real outlinks from TVT target Nodes, captures passing vehicles at each
outlink's terminal Node immediately before ``Node.transfer()``, and after a
successful transfer counts active timesteps and vehicles that left the monitored
outlink toward a further link. Trip-end (``vehicle.link is None``) is not counted
as a successful downstream pass.

This module does not run baseline forward, visit collection, FIFO checks, average
rates, or local virtual calculation. Integration with ``World.exec_simulation()``
is outside this module's scope until the driver connects an observer instance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(
            f"{field_name} must be a non-empty str; got {value!r}."
        )
    return value


def _require_non_negative_int_not_bool(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"{field_name} must be a non-negative int (not bool); got {value!r}."
        )
    return value


@dataclass(frozen=True)
class OrderControlBaselineDownstreamBoundaryOutlinkResult:
    """
    Observed counts for one monitored outlink (terminal boundary).

    Does not store the origin target Node name, objects, or derived average rates.
    """

    outlink_name: str
    terminal_node_name: str
    active_timestep_count: int
    transferred_vehicle_count: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "outlink_name",
            _require_non_empty_str(self.outlink_name, "outlink_name"),
        )
        object.__setattr__(
            self,
            "terminal_node_name",
            _require_non_empty_str(
                self.terminal_node_name,
                "terminal_node_name",
            ),
        )
        object.__setattr__(
            self,
            "active_timestep_count",
            _require_non_negative_int_not_bool(
                self.active_timestep_count,
                "active_timestep_count",
            ),
        )
        object.__setattr__(
            self,
            "transferred_vehicle_count",
            _require_non_negative_int_not_bool(
                self.transferred_vehicle_count,
                "transferred_vehicle_count",
            ),
        )


@dataclass(frozen=True)
class OrderControlBaselineDownstreamBoundaryNodeResult:
    """Per target-Node downstream boundary results in registration order."""

    node_name: str
    outlink_results: tuple[OrderControlBaselineDownstreamBoundaryOutlinkResult, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "node_name",
            _require_non_empty_str(self.node_name, "node_name"),
        )
        if not isinstance(self.outlink_results, tuple):
            raise ValueError(
                "outlink_results must be a tuple; "
                f"got {self.outlink_results!r}."
            )
        validated_outlinks: list[
            OrderControlBaselineDownstreamBoundaryOutlinkResult
        ] = []
        for index, outlink_result in enumerate(self.outlink_results):
            if not isinstance(
                outlink_result,
                OrderControlBaselineDownstreamBoundaryOutlinkResult,
            ):
                raise ValueError(
                    f"outlink_results[{index}] must be "
                    "OrderControlBaselineDownstreamBoundaryOutlinkResult; "
                    f"got {outlink_result!r}."
                )
            validated_outlinks.append(outlink_result)
        object.__setattr__(
            self,
            "outlink_results",
            tuple(validated_outlinks),
        )


@dataclass(frozen=True)
class OrderControlBaselineDownstreamBoundaryResult:
    """Overall downstream boundary observation result for one baseline run."""

    node_results: tuple[OrderControlBaselineDownstreamBoundaryNodeResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.node_results, tuple):
            raise ValueError(
                f"node_results must be a tuple; got {self.node_results!r}."
            )
        validated_nodes: list[
            OrderControlBaselineDownstreamBoundaryNodeResult
        ] = []
        for index, node_result in enumerate(self.node_results):
            if not isinstance(
                node_result,
                OrderControlBaselineDownstreamBoundaryNodeResult,
            ):
                raise ValueError(
                    f"node_results[{index}] must be "
                    "OrderControlBaselineDownstreamBoundaryNodeResult; "
                    f"got {node_result!r}."
                )
            validated_nodes.append(node_result)
        object.__setattr__(self, "node_results", tuple(validated_nodes))


@dataclass
class _RegisteredOutlinkState:
    """Mutable per-outlink counters and labels for one monitored outlink."""

    outlink: Any
    outlink_name: str
    terminal_node: Any
    terminal_node_name: str
    active_timestep_count: int = 0
    transferred_vehicle_count: int = 0


@dataclass
class _RegisteredTargetNodeState:
    """Registration-order anchor for one target Node and its outlinks."""

    target_node: Any
    node_name: str
    outlink_states: list[_RegisteredOutlinkState] = field(default_factory=list)


@dataclass
class _PendingTransferCapture:
    """One terminal Node's pre-transfer snapshot (not yet committed)."""

    terminal_node: Any
    # Each item: (outlink state, tuple of captured Vehicle references).
    outlink_vehicle_snapshots: list[tuple[_RegisteredOutlinkState, tuple[Any, ...]]]


class OrderControlBaselineDownstreamBoundaryObserver:
    """
    Observes downstream terminal boundaries for registered target-Node outlinks.

    Holds registration order, terminal-Node index, committed counts, and at most
    one pending capture between ``capture_before_transfer`` and commit/clear.
    """

    def __init__(self) -> None:
        # Export-order source of truth: target Nodes in registration order.
        self._target_node_states: list[_RegisteredTargetNodeState] = []
        # Duplicate registration detection (object identity via id(), not hashability).
        self._registered_target_node_ids: set[int] = set()
        self._registered_outlink_ids: set[int] = set()
        # Terminal Node id -> monitored outlink states at that terminal.
        self._outlink_states_by_terminal_node_id: dict[
            int, list[_RegisteredOutlinkState]
        ] = {}
        self._pending_capture: _PendingTransferCapture | None = None

    def register_target_node_outlinks(self, target_node: Any) -> None:
        """
        Register all outlinks of one target Node in ``target_node.outlinks`` order.

        Validates structure before changing internal state. Rejects duplicate target
        Nodes, duplicate outlink objects, and empty outlink sets.
        """
        node_name = _require_non_empty_str(
            getattr(target_node, "name", None),
            "target_node.name",
        )
        target_node_id = id(target_node)
        if target_node_id in self._registered_target_node_ids:
            raise ValueError(
                f"target Node {node_name!r} is already registered for "
                "downstream boundary observation."
            )

        outlinks_mapping = getattr(target_node, "outlinks", None)
        if not isinstance(outlinks_mapping, dict):
            raise ValueError(
                f"target_node.outlinks for Node {node_name!r} must be a dict; "
                f"got {outlinks_mapping!r}."
            )

        outlinks_in_registration_order = list(outlinks_mapping.values())
        if len(outlinks_in_registration_order) == 0:
            raise ValueError(
                f"target Node {node_name!r} has no outlinks to monitor; "
                "empty outlinks is not supported."
            )

        planned_outlink_states: list[_RegisteredOutlinkState] = []
        planned_outlink_ids: set[int] = set()
        for outlink in outlinks_in_registration_order:
            outlink_id = id(outlink)
            outlink_name_hint = getattr(outlink, "name", None)
            if outlink_id in self._registered_outlink_ids:
                raise ValueError(
                    f"outlink {outlink_name_hint!r} from target Node {node_name!r} "
                    "is already registered for downstream boundary observation."
                )
            if outlink_id in planned_outlink_ids:
                raise ValueError(
                    f"outlink {outlink_name_hint!r} from target Node {node_name!r} "
                    "is listed more than once in target_node.outlinks "
                    "(duplicate outlink object)."
                )
            planned_outlink_ids.add(outlink_id)

            outlink_name = _require_non_empty_str(
                getattr(outlink, "name", None),
                "outlink.name",
            )
            start_node = getattr(outlink, "start_node", None)
            if start_node is not target_node:
                raise ValueError(
                    f"outlink {outlink_name!r} start_node must be the "
                    f"registration target Node {node_name!r}."
                )
            terminal_node = getattr(outlink, "end_node", None)
            if terminal_node is None:
                raise ValueError(
                    f"outlink {outlink_name!r} from Node {node_name!r} "
                    "must have end_node set."
                )
            terminal_node_name = _require_non_empty_str(
                getattr(terminal_node, "name", None),
                "outlink.end_node.name",
            )

            planned_outlink_states.append(
                _RegisteredOutlinkState(
                    outlink=outlink,
                    outlink_name=outlink_name,
                    terminal_node=terminal_node,
                    terminal_node_name=terminal_node_name,
                )
            )

        # All checks passed; commit registration for this target Node.
        self._registered_target_node_ids.add(target_node_id)
        for outlink_state in planned_outlink_states:
            self._registered_outlink_ids.add(id(outlink_state.outlink))

        target_state = _RegisteredTargetNodeState(
            target_node=target_node,
            node_name=node_name,
            outlink_states=planned_outlink_states,
        )
        self._target_node_states.append(target_state)

        for outlink_state in planned_outlink_states:
            terminal_node_id = id(outlink_state.terminal_node)
            if terminal_node_id not in self._outlink_states_by_terminal_node_id:
                self._outlink_states_by_terminal_node_id[terminal_node_id] = []
            self._outlink_states_by_terminal_node_id[terminal_node_id].append(
                outlink_state
            )

    def capture_before_transfer(self, node: Any) -> bool:
        """
        Snapshot passing vehicles at a terminal Node before ``transfer()``.

        Returns True if ``node`` is a monitored outlink terminal and a pending
        capture was created. Returns False if ``node`` is not monitored. True
        does not mean that any vehicle was waiting. Does not change committed
        counts or mutate simulation state. Pending is assigned only after the
        snapshot is complete, so a failed capture leaves no pending.
        """
        if self._pending_capture is not None:
            raise RuntimeError(
                "capture_before_transfer called while a pending downstream "
                "boundary capture already exists; commit or clear_pending first."
            )

        terminal_node_id = id(node)
        monitored_outlink_states = self._outlink_states_by_terminal_node_id.get(
            terminal_node_id
        )
        if monitored_outlink_states is None:
            return False

        incoming_vehicles = getattr(node, "incoming_vehicles", None)
        if incoming_vehicles is None:
            incoming_vehicles = []

        outlink_vehicle_snapshots: list[
            tuple[_RegisteredOutlinkState, tuple[Any, ...]]
        ] = []
        for outlink_state in monitored_outlink_states:
            monitored_outlink = outlink_state.outlink
            captured_vehicles: list[Any] = []
            for vehicle in incoming_vehicles:
                vehicle_link = getattr(vehicle, "link", None)
                if vehicle_link is monitored_outlink:
                    captured_vehicles.append(vehicle)
            outlink_vehicle_snapshots.append(
                (outlink_state, tuple(captured_vehicles))
            )

        self._pending_capture = _PendingTransferCapture(
            terminal_node=node,
            outlink_vehicle_snapshots=outlink_vehicle_snapshots,
        )
        return True

    def commit_after_transfer(self, node: Any) -> None:
        """
        Commit active and transferred counts after a successful ``transfer()``.

        Clears pending on success so a following ``clear_pending()`` is a no-op.
        """
        pending = self._pending_capture
        if pending is None:
            raise RuntimeError(
                "commit_after_transfer called with no pending downstream "
                "boundary capture."
            )
        if pending.terminal_node is not node:
            pending_name = getattr(pending.terminal_node, "name", pending.terminal_node)
            commit_name = getattr(node, "name", node)
            raise RuntimeError(
                "commit_after_transfer node must match capture node; "
                f"capture was for {pending_name!r}, commit for {commit_name!r}."
            )

        for outlink_state, captured_vehicles in pending.outlink_vehicle_snapshots:
            if len(captured_vehicles) >= 1:
                outlink_state.active_timestep_count += 1
            monitored_outlink = outlink_state.outlink
            for vehicle in captured_vehicles:
                vehicle_link_after = getattr(vehicle, "link", None)
                if vehicle_link_after is None:
                    continue
                if vehicle_link_after is monitored_outlink:
                    continue
                outlink_state.transferred_vehicle_count += 1

        self._pending_capture = None

    def clear_pending(self) -> None:
        """Discard the current pending capture without changing committed counts."""
        self._pending_capture = None

    def export_result(self) -> OrderControlBaselineDownstreamBoundaryResult:
        """
        Build a frozen result from committed counts in registration order.

        Raises if a pending capture remains (uncommitted timestep).
        """
        if self._pending_capture is not None:
            raise RuntimeError(
                "export_result called while a pending downstream boundary "
                "capture exists; commit or clear_pending first."
            )

        node_results: list[OrderControlBaselineDownstreamBoundaryNodeResult] = []
        for target_state in self._target_node_states:
            outlink_results: list[
                OrderControlBaselineDownstreamBoundaryOutlinkResult
            ] = []
            for outlink_state in target_state.outlink_states:
                outlink_results.append(
                    OrderControlBaselineDownstreamBoundaryOutlinkResult(
                        outlink_name=outlink_state.outlink_name,
                        terminal_node_name=outlink_state.terminal_node_name,
                        active_timestep_count=outlink_state.active_timestep_count,
                        transferred_vehicle_count=(
                            outlink_state.transferred_vehicle_count
                        ),
                    )
                )
            node_results.append(
                OrderControlBaselineDownstreamBoundaryNodeResult(
                    node_name=target_state.node_name,
                    outlink_results=tuple(outlink_results),
                )
            )

        return OrderControlBaselineDownstreamBoundaryResult(
            node_results=tuple(node_results),
        )
