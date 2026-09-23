"""
Virtual clock and capacity refill for one candidate's copied World.

Offset 0 is baseline timestep T. It keeps the snapshot's remaining capacity.
Each later step moves the copied clock by one timestep and refills only the
target Node and the target inlinks and outlinks, using the same refill as
``Link.in_out_flow_constraint`` and ``Node.flow_capacity_update``.

This stage does not move vehicles or pass them through the Node.
"""

from __future__ import annotations

from uxsim.order_control_tvt_mp_candidate_local_state import (
    OrderControlTvtMpCandidateLocalState,
)
from uxsim.uxsim import World

# UXsim uses this sentinel when inflow capacity or node flow capacity is unset.
_UXSIM_UNLIMITED_CAPACITY_REMAIN = 10e10


class OrderControlTvtMpCandidateVirtualTimeState:
    """Mutable virtual clock for one candidate local state.

    ``current_offset`` is 0 at baseline timestep T and then 1, 2, 3, ...
    ``current_virtual_timestep`` is ``baseline_timestep_T + current_offset``.
    ``simulated_timestep_count`` counts how many times the virtual clock has
    moved past T. It is 0 while the candidate is still at T, and it equals
    ``current_offset`` after each one-step advance. It does not count the
    snapshot timestep itself.

    The fields are read through properties so a caller cannot point the clock
    at a different offset without the one-step advance.
    """

    def __init__(
        self,
        candidate_local_state: OrderControlTvtMpCandidateLocalState,
        baseline_timestep_T: int,
    ) -> None:
        self._candidate_local_state = candidate_local_state
        self._baseline_timestep_T = baseline_timestep_T
        self._current_offset = 0
        # Clock advances past T. Offset 0 has not advanced the clock.
        self._simulated_timestep_count = 0

    @property
    def candidate_local_state(self) -> OrderControlTvtMpCandidateLocalState:
        return self._candidate_local_state

    @property
    def baseline_timestep_T(self) -> int:
        return self._baseline_timestep_T

    @property
    def current_offset(self) -> int:
        return self._current_offset

    @property
    def current_virtual_timestep(self) -> int:
        return self._baseline_timestep_T + self._current_offset

    @property
    def simulated_timestep_count(self) -> int:
        return self._simulated_timestep_count


def _require_python_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValueError(
            f"{field_name} must be a Python int, not bool; got "
            f"type {type(value).__name__} with value {value!r}."
        )
    return value


def _require_positive_number(value: object, field_name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"{field_name} must be a positive int or float, not bool; got "
            f"type {type(value).__name__} with value {value!r}."
        )
    if value <= 0:
        raise ValueError(f"{field_name} must be > 0; got {value!r}.")
    return value


def _require_non_negative_number(value: object, field_name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"{field_name} must be a non-negative number, not bool; got "
            f"{value!r}."
        )
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0; got {value!r}.")
    return value


def _require_optional_non_negative_number(
    value: object,
    field_name: str,
) -> int | float | None:
    if value is None:
        return None
    return _require_non_negative_number(value, field_name)


def _require_local_world(
    candidate_local_state: OrderControlTvtMpCandidateLocalState,
) -> World:
    local_world = candidate_local_state.local_world
    if not isinstance(local_world, World):
        raise ValueError(
            "candidate_local_state.local_world must be a World; got "
            f"type {type(local_world).__name__}."
        )
    return local_world


def _require_initial_timesteps_match(
    candidate_local_state: OrderControlTvtMpCandidateLocalState,
    local_world: World,
) -> int:
    baseline_timestep_T = _require_python_int(
        candidate_local_state.binding_rank_sequence.baseline_timestep_T,
        "binding_rank_sequence.baseline_timestep_T",
    )
    if baseline_timestep_T < 0:
        raise ValueError(
            "binding_rank_sequence.baseline_timestep_T must be >= 0; "
            f"got {baseline_timestep_T}."
        )
    real_world_timestep_T = _require_python_int(
        candidate_local_state.real_world_timestep_T,
        "candidate_local_state.real_world_timestep_T",
    )
    local_timestep_T = _require_python_int(local_world.T, "local_world.T")
    if (
        local_timestep_T != baseline_timestep_T
        or real_world_timestep_T != baseline_timestep_T
    ):
        raise ValueError(
            "local virtual time must start at baseline timestep T; "
            f"local_world.T={local_timestep_T}, "
            f"real_world_timestep_T={real_world_timestep_T}, "
            f"baseline_timestep_T={baseline_timestep_T}."
        )
    return baseline_timestep_T


def _unique_local_links(
    candidate_local_state: OrderControlTvtMpCandidateLocalState,
) -> tuple[object, ...]:
    """Inlink registration order, then outlinks not already included.

    A link that is both an inlink and an outlink is refilled once.
    """
    unique_links: list[object] = []
    seen_link_ids: set[int] = set()
    for link in candidate_local_state.inlinks + candidate_local_state.outlinks:
        link_identity = id(link)
        if link_identity in seen_link_ids:
            continue
        seen_link_ids.add(link_identity)
        unique_links.append(link)
    return tuple(unique_links)


def _require_clock_is_consistent(
    virtual_time_state: OrderControlTvtMpCandidateVirtualTimeState,
) -> None:
    local_world = virtual_time_state.candidate_local_state.local_world
    current_offset = virtual_time_state.current_offset
    current_virtual_timestep = virtual_time_state.current_virtual_timestep
    expected_timestep = virtual_time_state.baseline_timestep_T + current_offset
    if current_virtual_timestep != expected_timestep:
        raise RuntimeError(
            "virtual timestep "
            f"{current_virtual_timestep} is not baseline "
            f"{virtual_time_state.baseline_timestep_T} + offset {current_offset}."
        )
    if local_world.T != current_virtual_timestep:
        raise RuntimeError(
            "copied World time "
            f"{local_world.T!r} does not match virtual timestep "
            f"{current_virtual_timestep}. The clock is not corrected "
            "automatically."
        )
    if virtual_time_state.simulated_timestep_count != current_offset:
        raise RuntimeError(
            "simulated_timestep_count "
            f"{virtual_time_state.simulated_timestep_count} does not equal "
            f"current_offset {current_offset}."
        )


def _require_world_step_sizes(local_world: World) -> tuple[int | float, int | float]:
    deltat = _require_positive_number(local_world.DELTAT, "local_world.DELTAT")
    deltan = _require_positive_number(local_world.DELTAN, "local_world.DELTAN")
    return deltat, deltan


def _next_link_capacity_remains(
    link: object,
    *,
    deltat: int | float,
    deltan: int | float,
) -> tuple[int | float, int | float]:
    """
    Same refill as ``Link.in_out_flow_constraint``.

    A finite link adds one timestep of capacity only while the remainder is
    below ``DELTAN * number_of_lanes``. An unset ``capacity_in`` means both
    remainders become UXsim's unlimited sentinel.
    """
    link_name = getattr(link, "name", None)
    if not isinstance(link_name, str) or link_name == "":
        raise ValueError("a local link has no name for capacity refill.")
    capacity_in = _require_optional_non_negative_number(
        getattr(link, "capacity_in", None),
        f"link {link_name}.capacity_in",
    )
    capacity_out_remain = _require_non_negative_number(
        getattr(link, "capacity_out_remain", None),
        f"link {link_name}.capacity_out_remain",
    )
    capacity_in_remain = _require_non_negative_number(
        getattr(link, "capacity_in_remain", None),
        f"link {link_name}.capacity_in_remain",
    )
    if capacity_in is None:
        return (
            _UXSIM_UNLIMITED_CAPACITY_REMAIN,
            _UXSIM_UNLIMITED_CAPACITY_REMAIN,
        )
    capacity_out = _require_non_negative_number(
        getattr(link, "capacity_out", None),
        f"link {link_name}.capacity_out",
    )
    number_of_lanes = _require_python_int(
        getattr(link, "number_of_lanes", None),
        f"link {link_name}.number_of_lanes",
    )
    if number_of_lanes < 1:
        raise ValueError(
            f"link {link_name}.number_of_lanes must be >= 1; "
            f"got {number_of_lanes}."
        )
    refill_threshold = deltan * number_of_lanes
    next_capacity_out_remain = capacity_out_remain
    next_capacity_in_remain = capacity_in_remain
    if capacity_out_remain < refill_threshold:
        next_capacity_out_remain = capacity_out_remain + capacity_out * deltat
    if capacity_in_remain < refill_threshold:
        next_capacity_in_remain = capacity_in_remain + capacity_in * deltat
    return next_capacity_out_remain, next_capacity_in_remain


def _next_node_flow_capacity_remain(
    node: object,
    *,
    deltat: int | float,
    deltan: int | float,
) -> int | float:
    """Same refill as ``Node.flow_capacity_update`` for one finite or unset node."""
    node_name = getattr(node, "name", None)
    if not isinstance(node_name, str) or node_name == "":
        raise ValueError("the target Node has no name for capacity refill.")
    flow_capacity = _require_optional_non_negative_number(
        getattr(node, "flow_capacity", None),
        f"node {node_name}.flow_capacity",
    )
    flow_capacity_remain = _require_non_negative_number(
        getattr(node, "flow_capacity_remain", None),
        f"node {node_name}.flow_capacity_remain",
    )
    if flow_capacity is None:
        return _UXSIM_UNLIMITED_CAPACITY_REMAIN
    number_of_lanes = _require_python_int(
        getattr(node, "number_of_lanes", None),
        f"node {node_name}.number_of_lanes",
    )
    if number_of_lanes < 1:
        raise ValueError(
            f"node {node_name}.number_of_lanes must be >= 1; "
            f"got {number_of_lanes}."
        )
    if flow_capacity_remain < deltan * number_of_lanes:
        return flow_capacity_remain + flow_capacity * deltat
    return flow_capacity_remain


def _extended_cumulative_counts(
    counts: object,
    *,
    virtual_timestep: int,
    link_name: str,
    field_name: str,
) -> list:
    """
    Copy the last count forward until index ``virtual_timestep`` exists.

    ``Link.update`` appends the previous cumulative value. BATCH Level 2
    repeats that until ``len(counts) > W.T``. Past entries are not rewritten.
    """
    if not isinstance(counts, list):
        raise RuntimeError(
            f"link {link_name}.{field_name} must be a list to extend through "
            f"virtual timestep {virtual_timestep}; got "
            f"type {type(counts).__name__}."
        )
    extended_counts = list(counts)
    while len(extended_counts) <= virtual_timestep:
        if len(extended_counts) == 0:
            extended_counts.append(0)
        else:
            extended_counts.append(extended_counts[-1])
    return extended_counts


def _extend_local_cumulative_arrays(
    links: tuple[object, ...],
    virtual_timestep: int,
) -> None:
    prepared_arrays: list[tuple[object, list, list]] = []
    for link in links:
        link_name = link.name
        next_cum_arrival = _extended_cumulative_counts(
            link.cum_arrival,
            virtual_timestep=virtual_timestep,
            link_name=link_name,
            field_name="cum_arrival",
        )
        next_cum_departure = _extended_cumulative_counts(
            link.cum_departure,
            virtual_timestep=virtual_timestep,
            link_name=link_name,
            field_name="cum_departure",
        )
        prepared_arrays.append((link, next_cum_arrival, next_cum_departure))
    for link, next_cum_arrival, next_cum_departure in prepared_arrays:
        if len(next_cum_arrival) != len(link.cum_arrival):
            link.cum_arrival = next_cum_arrival
        if len(next_cum_departure) != len(link.cum_departure):
            link.cum_departure = next_cum_departure


def initialize_tvt_mp_candidate_virtual_time_state(
    candidate_local_state: OrderControlTvtMpCandidateLocalState,
) -> OrderControlTvtMpCandidateVirtualTimeState:
    """
    Start one candidate clock at baseline timestep T without refilling capacity.

    Cumulative arrival and departure lists are extended to index T when the
    snapshot list is shorter, so a later write at T has a slot. Capacity,
    vehicles, incoming vehicles, and clearance history stay as copied.
    """
    if not isinstance(candidate_local_state, OrderControlTvtMpCandidateLocalState):
        raise ValueError(
            "candidate_local_state must be OrderControlTvtMpCandidateLocalState; "
            f"got type {type(candidate_local_state).__name__}."
        )
    local_world = _require_local_world(candidate_local_state)
    baseline_timestep_T = _require_initial_timesteps_match(
        candidate_local_state,
        local_world,
    )
    _require_world_step_sizes(local_world)
    local_links = _unique_local_links(candidate_local_state)
    _extend_local_cumulative_arrays(local_links, baseline_timestep_T)
    return OrderControlTvtMpCandidateVirtualTimeState(
        candidate_local_state,
        baseline_timestep_T,
    )


def advance_tvt_mp_candidate_virtual_time_one_step(
    virtual_time_state: OrderControlTvtMpCandidateVirtualTimeState,
) -> OrderControlTvtMpCandidateVirtualTimeState:
    """
    Move the copied clock one timestep and refill local capacity once.

    The next remainders and cumulative lists are calculated before any clock
    or capacity field is written. Vehicles are not moved.
    """
    if not isinstance(
        virtual_time_state,
        OrderControlTvtMpCandidateVirtualTimeState,
    ):
        raise ValueError(
            "virtual_time_state must be "
            "OrderControlTvtMpCandidateVirtualTimeState; got "
            f"type {type(virtual_time_state).__name__}."
        )
    _require_clock_is_consistent(virtual_time_state)
    candidate_local_state = virtual_time_state.candidate_local_state
    local_world = _require_local_world(candidate_local_state)
    deltat, deltan = _require_world_step_sizes(local_world)
    local_links = _unique_local_links(candidate_local_state)
    target_node = candidate_local_state.target_node
    next_offset = virtual_time_state.current_offset + 1
    next_virtual_timestep = virtual_time_state.baseline_timestep_T + next_offset

    next_link_remains = []
    for link in local_links:
        next_capacity_out_remain, next_capacity_in_remain = (
            _next_link_capacity_remains(
                link,
                deltat=deltat,
                deltan=deltan,
            )
        )
        next_link_remains.append(
            (link, next_capacity_out_remain, next_capacity_in_remain)
        )
    next_flow_capacity_remain = _next_node_flow_capacity_remain(
        target_node,
        deltat=deltat,
        deltan=deltan,
    )
    next_cumulative_arrays = []
    for link in local_links:
        next_cumulative_arrays.append(
            (
                link,
                _extended_cumulative_counts(
                    link.cum_arrival,
                    virtual_timestep=next_virtual_timestep,
                    link_name=link.name,
                    field_name="cum_arrival",
                ),
                _extended_cumulative_counts(
                    link.cum_departure,
                    virtual_timestep=next_virtual_timestep,
                    link_name=link.name,
                    field_name="cum_departure",
                ),
            )
        )

    local_world.T = next_virtual_timestep
    for link, next_capacity_out_remain, next_capacity_in_remain in next_link_remains:
        link.capacity_out_remain = next_capacity_out_remain
        link.capacity_in_remain = next_capacity_in_remain
    target_node.flow_capacity_remain = next_flow_capacity_remain
    for link, next_cum_arrival, next_cum_departure in next_cumulative_arrays:
        if len(next_cum_arrival) != len(link.cum_arrival):
            link.cum_arrival = next_cum_arrival
        if len(next_cum_departure) != len(link.cum_departure):
            link.cum_departure = next_cum_departure
    virtual_time_state._current_offset = next_offset
    virtual_time_state._simulated_timestep_count = next_offset
    return virtual_time_state
