"""
Production-unchanged route-choice RNG diagnostic for a later small invariance trial.

This module does not modify production files. It temporarily replaces
``Node.generate`` and ``Vehicle.route_next_link_choice`` in one Python process,
records real-World route-choice draws, and restores the original methods.

This is not keyed randomization.
This is not a production seed or RNG change.
This is not the four-method common seed/RNG framework.

The diagnostic never draws an extra random number. The temporary proxy calls
the original ``Generator.choice`` once for each production ``choice`` call, and
it reads ``bit_generator.state`` only to fingerprint that state.

Only the real World passed to the session is recorded. Baseline forks and
candidate local Worlds are pickle copies. Their ``generate`` and
``route_next_link_choice`` calls run the original production method once, with
no proxy and no event.

The proxy is installed only while one target method is running. It is not left
on ``World.rng``. If pickle or dill tries to serialize the proxy, the proxy
raises ``RuntimeError``.

A normal end and an exception both put the original Generator object back on
``World.rng``. ``restore_route_choice_rng_diagnostic`` puts the original class
methods back in reverse order of installation. Call it from ``finally``.
This module does not register ``atexit``.

Creating this module does not show that a run with the diagnostic matches a
run without it. Version 1 is for a later small invariance trial only. Do not
use it for a 3,000-vehicle formal run yet.

Caller shape::

    session = RouteChoiceRngDiagnosticSession(real_world, run_method)
    install_route_choice_rng_diagnostic(session)
    try:
        real_world.exec_simulation()
    finally:
        restore_route_choice_rng_diagnostic(session)
    validate_restored_route_choice_rng_diagnostic(session)

The public functions take the session object. The class-method wrappers reach
that same session through the one module-level active session. A second
install is refused.
"""

from __future__ import annotations

import copy
import hashlib
import json

import numpy as np


# Probability values are recorded, not judged, by the simulation path.
# A later trial can read both vectors. This tolerance is only the stored
# comparison flag. A mismatch does not draw again and does not change the
# selected link.
PROBABILITY_MATCH_RELATIVE_TOLERANCE = 1e-9
PROBABILITY_MATCH_ABSOLUTE_TOLERANCE = 1e-12

WORLD_KIND_REAL = "real"
EVENT_KIND_ORIGIN = "origin"
EVENT_KIND_IN_TRIP = "in_trip"

PROBABILITY_MODE_OMITTED = "omitted"
PROBABILITY_MODE_EXPLICIT_NONE = "explicit_none"
PROBABILITY_MODE_PROVIDED = "provided"

ORIGIN_ADMISSION_ACCEPTED = "accepted"
ORIGIN_ADMISSION_REJECTED = "rejected"

_ACTIVE_SESSION = None


# ---------------------------------------------------------------------------
# 1. Event record
# ---------------------------------------------------------------------------


class RouteChoiceRngDiagnosticEvent:
    """One observed route-choice attempt on the real World.

    Missing values are ``None`` or an empty tuple. They are not dummy numbers
    or placeholder link names.

    ``route_choice_ordinal`` is set only when production actually called
    ``W.rng.choice``. A non-draw call keeps it as ``None``.

    ``rng_state_canonical_json_before`` and ``rng_state_canonical_json_after``
    are the fingerprint inputs. They are not pickle bytes.

    ``recomputed_normalized_probability_vector`` is calculated from the raw
    preference read at the choice moment. It is not passed to ``choice``.
    ``provided_probability_matches_recomputed`` compares that vector with the
    ``p`` argument production actually passed. It is ``None`` when production
    did not pass a probability vector.
    """

    def __init__(
        self,
        run_method,
        world_kind,
        event_kind,
        vehicle_name,
        route_choice_ordinal,
        attempt_ordinal_at_location,
        decision_timestep,
        decision_node_name,
        current_link_name,
        ordered_candidate_link_names,
        raw_preference_vector,
        normalized_probability_vector,
        probability_mode,
        rng_state_fingerprint_before,
        selected_link_name,
        rng_state_fingerprint_after,
        specified_route_used,
        hard_deterministic_mode,
        links_prefer_names,
        links_avoid_names,
        choice_called,
        origin_admission,
        route_history_before,
        rng_state_canonical_json_before,
        rng_state_canonical_json_after,
        recomputed_normalized_probability_vector,
        provided_probability_matches_recomputed,
    ):
        self.run_method = run_method
        self.world_kind = world_kind
        self.event_kind = event_kind
        self.vehicle_name = vehicle_name
        self.route_choice_ordinal = route_choice_ordinal
        self.attempt_ordinal_at_location = attempt_ordinal_at_location
        self.decision_timestep = decision_timestep
        self.decision_node_name = decision_node_name
        self.current_link_name = current_link_name
        self.ordered_candidate_link_names = ordered_candidate_link_names
        self.raw_preference_vector = raw_preference_vector
        self.normalized_probability_vector = normalized_probability_vector
        self.probability_mode = probability_mode
        self.rng_state_fingerprint_before = rng_state_fingerprint_before
        self.selected_link_name = selected_link_name
        self.rng_state_fingerprint_after = rng_state_fingerprint_after
        self.specified_route_used = specified_route_used
        self.hard_deterministic_mode = hard_deterministic_mode
        self.links_prefer_names = links_prefer_names
        self.links_avoid_names = links_avoid_names
        self.choice_called = choice_called
        self.origin_admission = origin_admission
        self.route_history_before = route_history_before
        self.rng_state_canonical_json_before = rng_state_canonical_json_before
        self.rng_state_canonical_json_after = rng_state_canonical_json_after
        self.recomputed_normalized_probability_vector = (
            recomputed_normalized_probability_vector
        )
        self.provided_probability_matches_recomputed = (
            provided_probability_matches_recomputed
        )


# ---------------------------------------------------------------------------
# 2. RNG state canonical form and fingerprint
# ---------------------------------------------------------------------------


def _canonicalize_rng_state_value(value):
    """Convert one state value into a JSON-stable form.

    This function does not call ``random``, ``choice``, ``uniform``, or any
    other Generator method. Python ``bool`` and NumPy boolean values stay
    booleans. They are not turned into integers.

    ``bytes`` and ``bytearray`` become ``{"__bytes_hex__": "<hex>"}``. The
    current NumPy Generator state used by UXsim is integer-based. The bytes
    contract is here so an unexpected byte string cannot be pickled or hashed
    with Python's built-in ``hash``.
    """
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return {"__bytes_hex__": bytes(value).hex()}
    if isinstance(value, np.ndarray):
        converted = []
        for item in value.tolist():
            converted.append(_canonicalize_rng_state_value(item))
        return converted
    if isinstance(value, (list, tuple)):
        converted = []
        for item in value:
            converted.append(_canonicalize_rng_state_value(item))
        return converted
    if isinstance(value, dict):
        converted = {}
        for key in sorted(value.keys(), key=_rng_state_dict_key_sort_text):
            if not isinstance(key, str):
                raise RuntimeError(
                    "RNG state dictionary key must be str before canonical JSON; "
                    f"got {type(key).__name__}."
                )
            converted[key] = _canonicalize_rng_state_value(value[key])
        return converted
    raise RuntimeError(
        "RNG state value cannot be canonicalized: "
        f"type {type(value).__name__}."
    )


def _rng_state_dict_key_sort_text(key):
    return str(key)


def capture_rng_state_fingerprint(generator):
    """Read Generator state and return canonical JSON plus its SHA-256 hex.

    The returned tuple is ``(canonical_json, sha256_hex)``. The snapshot is a
    ``copy.deepcopy`` of ``bit_generator.state``. Nothing is drawn.
    """
    if not isinstance(generator, np.random.Generator):
        raise RuntimeError(
            "RNG fingerprint source must be numpy.random.Generator; got "
            f"{type(generator).__name__}."
        )
    state_snapshot = copy.deepcopy(generator.bit_generator.state)
    canonical_state = _canonicalize_rng_state_value(state_snapshot)
    canonical_json = json.dumps(
        canonical_state,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    fingerprint = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return canonical_json, fingerprint


# ---------------------------------------------------------------------------
# 3. Small reads used by both wrappers
# ---------------------------------------------------------------------------


def _link_name(link):
    if link is None:
        return None
    name = getattr(link, "name", None)
    if not isinstance(name, str):
        raise RuntimeError(
            "Route-choice diagnostic expected a Link name; got "
            f"{type(link).__name__}."
        )
    return name


def _link_names_from_link_list(links):
    names = []
    for link in links:
        names.append(_link_name(link))
    return tuple(names)


def _route_history_before(vehicle):
    """Copy ``log_t_link`` labels without changing the vehicle.

    A stored label may be ``"home"``, ``"end"``, or a Link object. Entered
    links are recorded here. A link-end redraw that does not enter a new link
    does not add a row, so this history is not a choice counter.
    """
    names = []
    for entry in vehicle.log_t_link:
        label = entry[1]
        if isinstance(label, str):
            names.append(label)
            continue
        names.append(_link_name(label))
    return tuple(names)


def _read_choice_candidates(args, kwargs):
    """Return the candidate sequence production passed to ``choice``.

    The sequence order is kept. This function does not sort it and does not
    rebuild it from route preference.
    """
    if len(args) >= 1:
        return args[0]
    if "a" in kwargs:
        return kwargs["a"]
    raise RuntimeError("Generator.choice was called without a candidate sequence.")


def _candidate_links_and_names(candidate_sequence):
    links = []
    names = []
    for item in candidate_sequence:
        links.append(item)
        names.append(_link_name(item))
    return tuple(links), tuple(names)


def _read_probability_argument(kwargs):
    """Distinguish an omitted ``p`` from an explicit ``p=None``.

    Returns ``(probability_mode, normalized_vector_or_none)``. The normalized
    vector is a tuple of Python floats only when production passed a vector.
    """
    if "p" not in kwargs:
        return PROBABILITY_MODE_OMITTED, None
    passed_probability = kwargs["p"]
    if passed_probability is None:
        return PROBABILITY_MODE_EXPLICIT_NONE, None
    values = []
    for item in passed_probability:
        if isinstance(item, (bool, np.bool_)):
            raise RuntimeError(
                "Route-choice probability contained a bool. "
                "Refusing to treat it as a float."
            )
        values.append(float(item))
    return PROBABILITY_MODE_PROVIDED, tuple(values)


def _raw_preference_vector(vehicle, candidate_links):
    """Read ``vehicle.route_pref`` for the links just passed to ``choice``."""
    preference_table = vehicle.route_pref
    if preference_table is None:
        raise RuntimeError(
            f"Vehicle {vehicle.name} has no route_pref at the choice moment."
        )
    values = []
    for link in candidate_links:
        values.append(float(preference_table[link.id]))
    return tuple(values)


def _recomputed_normalized_probability(raw_preference_vector):
    """Normalize raw preference for comparison only. Do not pass it to choice."""
    if raw_preference_vector is None:
        return None
    total = 0.0
    for value in raw_preference_vector:
        total = total + value
    if total <= 0.0:
        return None
    normalized = []
    for value in raw_preference_vector:
        normalized.append(value / total)
    return tuple(normalized)


def _probability_values_match(left, right):
    if left is None or right is None:
        return False
    if len(left) != len(right):
        return False
    index = 0
    while index < len(left):
        difference = abs(left[index] - right[index])
        scale = abs(right[index])
        if difference > (
            PROBABILITY_MATCH_ABSOLUTE_TOLERANCE
            + PROBABILITY_MATCH_RELATIVE_TOLERANCE * scale
        ):
            return False
        index = index + 1
    return True


def _vehicle_is_in_generation_queue(node, vehicle):
    for queued_vehicle in node.generation_queue:
        if queued_vehicle is vehicle:
            return True
    return False


# ---------------------------------------------------------------------------
# 4. Decision-location keys
# ---------------------------------------------------------------------------


def decision_location_parts(event):
    """Location identity without a vehicle name and without an attempt number.

    Timestep is intentionally absent. A later retry at the same place has a
    different timestep and a larger attempt number.
    """
    return (
        event.event_kind,
        event.decision_node_name,
        event.current_link_name,
        event.route_history_before,
    )


def decision_location_key(event):
    """Vehicle plus decision location. This is not a final FCFS/TVT pair key."""
    return (event.vehicle_name,) + decision_location_parts(event)


def draw_history_key(event):
    """Vehicle draw counter key. This is not a final FCFS/TVT pair key."""
    return (event.run_method, event.vehicle_name, event.route_choice_ordinal)


def decision_location_attempt_key(event):
    """Location key plus the attempt number at that location.

    This is not a final rule for pairing FCFS with TVT-MP.
    """
    return decision_location_key(event) + (event.attempt_ordinal_at_location,)


def _location_counter_key(
    vehicle_name,
    event_kind,
    decision_node_name,
    current_link_name,
    route_history_before,
):
    return (
        vehicle_name,
        event_kind,
        decision_node_name,
        current_link_name,
        route_history_before,
    )


# ---------------------------------------------------------------------------
# 5. Context objects held by the session, not by the World
# ---------------------------------------------------------------------------


class NodeGenerateDiagnosticContext:
    """State for one real-World ``Node.generate`` call."""

    def __init__(self, node, original_generator):
        self.node = node
        self.original_generator = original_generator
        self.observations = []


class OriginChoiceObservation:
    """One origin ``choice`` whose admission is classified after generate."""

    def __init__(self, event, vehicle, selected_link):
        self.event = event
        self.vehicle = vehicle
        self.selected_link = selected_link


class RouteNextLinkChoiceDiagnosticContext:
    """Facts copied before one real-World ``route_next_link_choice`` call."""

    def __init__(
        self,
        vehicle,
        vehicle_name,
        current_link_name,
        decision_node_name,
        decision_timestep,
        route_history_before,
        specified_route_used,
        hard_deterministic_mode,
        links_prefer_names,
        links_avoid_names,
    ):
        self.vehicle = vehicle
        self.vehicle_name = vehicle_name
        self.current_link_name = current_link_name
        self.decision_node_name = decision_node_name
        self.decision_timestep = decision_timestep
        self.route_history_before = route_history_before
        self.specified_route_used = specified_route_used
        self.hard_deterministic_mode = hard_deterministic_mode
        self.links_prefer_names = links_prefer_names
        self.links_avoid_names = links_avoid_names


# ---------------------------------------------------------------------------
# 6. Diagnostic session / ledger
# ---------------------------------------------------------------------------


class RouteChoiceRngDiagnosticSession:
    """Ledger for one real World. It is not stored on the World.

    ``draw_ordinal_by_vehicle_name`` counts actual ``choice`` calls across
    origin and in-trip draws. ``attempt_ordinal_by_location`` counts those
    same calls separately for each vehicle and decision location.

    A non-draw ``route_next_link_choice`` does not advance either counter.
    """

    def __init__(self, real_world, run_method):
        if real_world is None:
            raise RuntimeError("real_world is required.")
        if not isinstance(run_method, str) or run_method == "":
            raise RuntimeError("run_method must be a non-empty str.")
        self.real_world = real_world
        self.run_method = run_method
        self.events = []
        self.draw_ordinal_by_vehicle_name = {}
        self.attempt_ordinal_by_location = {}
        self.generate_context = None
        self.route_choice_context = None
        self.original_node_generate = None
        self.original_route_next_link_choice = None
        self.original_generator = None
        self.uxsim_module = None
        self.patches = []
        self.virtual_node_generate_pass_count = 0
        self.virtual_route_choice_pass_count = 0
        self.real_node_generate_pass_count = 0
        self.real_route_choice_pass_count = 0
        self.node_generate_success_count = 0
        self.route_choice_success_count = 0
        self.generator_restore_confirmed_count = 0
        self.generator_restore_failure_messages = []
        self.proxy_pickle_rejection_count = 0
        self.call_count_violation_messages = []
        self.installed = False

    def allocate_draw_ordinal(self, vehicle_name):
        previous = self.draw_ordinal_by_vehicle_name.get(vehicle_name, 0)
        allocated = previous + 1
        self.draw_ordinal_by_vehicle_name[vehicle_name] = allocated
        return allocated

    def allocate_attempt_ordinal(
        self,
        vehicle_name,
        event_kind,
        decision_node_name,
        current_link_name,
        route_history_before,
    ):
        key = _location_counter_key(
            vehicle_name,
            event_kind,
            decision_node_name,
            current_link_name,
            route_history_before,
        )
        previous = self.attempt_ordinal_by_location.get(key, 0)
        allocated = previous + 1
        self.attempt_ordinal_by_location[key] = allocated
        return allocated


def route_choice_diagnostic_events(session):
    """Return the recorded events. This does not write a file."""
    return tuple(session.events)


def _require_active_session():
    if _ACTIVE_SESSION is None:
        raise RuntimeError(
            "Route-choice diagnostic wrapper ran without an active session."
        )
    return _ACTIVE_SESSION


def _refuse_nested_context(session, wrapper_name):
    if session.generate_context is not None or session.route_choice_context is not None:
        raise RuntimeError(
            f"{wrapper_name} found an open diagnostic context. "
            "Nested Node.generate or route_next_link_choice diagnostics "
            "are refused."
        )


def _restore_temporary_generator(
    session,
    world,
    original_generator,
    context_name,
    production_returned,
):
    """Put the saved Generator back and clear the open method context.

    Called from ``finally``. When the production method raised,
    ``production_returned`` is false and this function does not raise, so the
    production exception continues. When the production method returned and the
    Generator object was not restored, this function raises.
    """
    world.rng = original_generator
    if context_name == "generate":
        session.generate_context = None
    elif context_name == "route":
        session.route_choice_context = None
    else:
        message = f"Unknown diagnostic context name {context_name!r}."
        session.generator_restore_failure_messages.append(message)
        if production_returned:
            raise RuntimeError(message)
        return
    if world.rng is original_generator:
        session.generator_restore_confirmed_count += 1
        return
    message = "World.rng was not restored to the original Generator object."
    session.generator_restore_failure_messages.append(message)
    if production_returned:
        raise RuntimeError(message)


def _require_one_original_call(session, called, method_name):
    if called == 1:
        return
    message = (
        f"{method_name} returned without calling the original production "
        f"method exactly once; call count was {called}."
    )
    session.call_count_violation_messages.append(message)
    raise RuntimeError(message)


# ---------------------------------------------------------------------------
# 7. Temporary RNG proxy
# ---------------------------------------------------------------------------


class RouteChoiceDiagnosticRngProxy:
    """Proxy installed only for the duration of one target production method.

    ``choice`` forwards ``*args`` and ``**kwargs`` to the original Generator
    once. No other Generator method is forwarded. ``__getattr__`` is not
    defined, so ``random``, ``uniform``, and ``shuffle`` raise
    ``AttributeError`` instead of drawing.
    """

    def __init__(self, session, original_generator):
        if not isinstance(original_generator, np.random.Generator):
            raise RuntimeError(
                "Diagnostic RNG proxy requires numpy.random.Generator; got "
                f"{type(original_generator).__name__}."
            )
        self.session = session
        self.original_generator = original_generator
        self.choice_call_count = 0

    @property
    def bit_generator(self):
        return self.original_generator.bit_generator

    def choice(self, *args, **kwargs):
        """Record one production choice and call the original choice once."""
        self.choice_call_count = self.choice_call_count + 1
        session = self.session
        if session.generate_context is not None and session.route_choice_context is not None:
            raise RuntimeError(
                "Both origin and in-trip diagnostic contexts were open at choice."
            )
        if session.generate_context is None and session.route_choice_context is None:
            raise RuntimeError(
                "Diagnostic RNG proxy received choice outside a target method."
            )

        # Draw first. Later logging must not call choice again, and it must
        # not skip this one production draw if reading names or preferences fails.
        canonical_before, fingerprint_before = capture_rng_state_fingerprint(
            self.original_generator
        )
        selected = self.original_generator.choice(*args, **kwargs)
        canonical_after, fingerprint_after = capture_rng_state_fingerprint(
            self.original_generator
        )

        candidate_sequence = _read_choice_candidates(args, kwargs)
        candidate_links, candidate_names = _candidate_links_and_names(
            candidate_sequence
        )
        probability_mode, normalized_probability_vector = _read_probability_argument(
            kwargs
        )
        # Node.generate has not continued yet, so a rejected vehicle is still
        # generation_queue[0]. route_pref is unchanged by Generator.choice.
        if session.generate_context is not None:
            vehicle = _origin_vehicle_before_choice(session.generate_context)
            event_kind = EVENT_KIND_ORIGIN
            decision_node_name = session.generate_context.node.name
            current_link_name = _link_name(vehicle.link)
            decision_timestep = session.generate_context.node.W.T
            route_history = _route_history_before(vehicle)
            specified_route_used = vehicle.specified_route is not None
            hard_deterministic_mode = bool(vehicle.W.hard_deterministic_mode)
            links_prefer_names = _link_names_from_link_list(vehicle.links_prefer)
            links_avoid_names = _link_names_from_link_list(vehicle.links_avoid)
        else:
            context = session.route_choice_context
            vehicle = context.vehicle
            event_kind = EVENT_KIND_IN_TRIP
            decision_node_name = context.decision_node_name
            current_link_name = context.current_link_name
            decision_timestep = context.decision_timestep
            route_history = context.route_history_before
            specified_route_used = context.specified_route_used
            hard_deterministic_mode = context.hard_deterministic_mode
            links_prefer_names = context.links_prefer_names
            links_avoid_names = context.links_avoid_names

        raw_preference_vector = _raw_preference_vector(vehicle, candidate_links)
        recomputed_normalized = _recomputed_normalized_probability(
            raw_preference_vector
        )
        if probability_mode == PROBABILITY_MODE_PROVIDED:
            probability_matches = _probability_values_match(
                normalized_probability_vector,
                recomputed_normalized,
            )
        else:
            probability_matches = None
        selected_link_name = _link_name(selected)

        draw_ordinal = session.allocate_draw_ordinal(vehicle.name)
        attempt_ordinal = session.allocate_attempt_ordinal(
            vehicle.name,
            event_kind,
            decision_node_name,
            current_link_name,
            route_history,
        )
        event = RouteChoiceRngDiagnosticEvent(
            run_method=session.run_method,
            world_kind=WORLD_KIND_REAL,
            event_kind=event_kind,
            vehicle_name=vehicle.name,
            route_choice_ordinal=draw_ordinal,
            attempt_ordinal_at_location=attempt_ordinal,
            decision_timestep=decision_timestep,
            decision_node_name=decision_node_name,
            current_link_name=current_link_name,
            ordered_candidate_link_names=candidate_names,
            raw_preference_vector=raw_preference_vector,
            normalized_probability_vector=normalized_probability_vector,
            probability_mode=probability_mode,
            rng_state_fingerprint_before=fingerprint_before,
            selected_link_name=selected_link_name,
            rng_state_fingerprint_after=fingerprint_after,
            specified_route_used=specified_route_used,
            hard_deterministic_mode=hard_deterministic_mode,
            links_prefer_names=links_prefer_names,
            links_avoid_names=links_avoid_names,
            choice_called=True,
            origin_admission=None,
            route_history_before=route_history,
            rng_state_canonical_json_before=canonical_before,
            rng_state_canonical_json_after=canonical_after,
            recomputed_normalized_probability_vector=recomputed_normalized,
            provided_probability_matches_recomputed=probability_matches,
        )
        session.events.append(event)
        if session.generate_context is not None:
            session.generate_context.observations.append(
                OriginChoiceObservation(event, vehicle, selected)
            )
        return selected

    def _refuse_pickle(self):
        self.session.proxy_pickle_rejection_count += 1
        raise RuntimeError(
            "Route-choice diagnostic RNG proxy must not be pickled. "
            "The proxy may be installed only while a target method is running."
        )

    def __reduce__(self):
        self._refuse_pickle()

    def __reduce_ex__(self, protocol):
        self._refuse_pickle()

    def __getstate__(self):
        self._refuse_pickle()


def _origin_vehicle_before_choice(generate_context):
    """Read ``generation_queue[0]`` while ``Node.generate`` is still inside choice.

    Production reads that vehicle before ``choice`` and pops it only after
    ``choice`` returns and admission succeeds. Until this proxy returns, the
    same vehicle is still at the front of the queue.
    """
    node = generate_context.node
    if len(node.generation_queue) == 0:
        raise RuntimeError(
            f"Node {node.name} called route choice with an empty generation queue."
        )
    return node.generation_queue[0]


# ---------------------------------------------------------------------------
# 8. Node.generate wrapper
# ---------------------------------------------------------------------------


def diagnostic_node_generate(node):
    """Real-World origin choices are recorded. Copies run the original once.

    On the real World, each ``W.rng.choice`` inside this one call becomes its
    own event. Admission is classified only after the original method returns.
    ``accepted`` means the same vehicle is ``run`` and ``vehicle.link is`` the
    selected Link. ``rejected`` means the same vehicle is ``wait`` and is still
    in this node's generation queue. Any other combination raises.

    Production breaks out of the departure loop on rejection, so a rejected
    event must be the last choice of this call.
    """
    session = _require_active_session()
    world = node.W
    if world is not session.real_world:
        session.virtual_node_generate_pass_count += 1
        called = 0
        session.original_node_generate(node)
        called = 1
        _require_one_original_call(session, called, "virtual Node.generate")
        return

    session.real_node_generate_pass_count += 1
    _refuse_nested_context(session, "Node.generate")
    original_generator = world.rng
    if original_generator is not session.original_generator:
        raise RuntimeError(
            "Real World rng is not the Generator captured when the diagnostic "
            "was installed."
        )
    if not isinstance(original_generator, np.random.Generator):
        raise RuntimeError(
            "Real World rng must be numpy.random.Generator before Node.generate; "
            f"got {type(original_generator).__name__}."
        )

    generate_context = NodeGenerateDiagnosticContext(node, original_generator)
    session.generate_context = generate_context
    proxy = RouteChoiceDiagnosticRngProxy(session, original_generator)
    world.rng = proxy
    called = 0
    try:
        session.original_node_generate(node)
        called = 1
    finally:
        _restore_temporary_generator(
            session,
            world,
            original_generator,
            "generate",
            called == 1,
        )
    _require_one_original_call(session, called, "Node.generate")
    _classify_origin_admissions(node, generate_context.observations)
    if len(generate_context.observations) != proxy.choice_call_count:
        raise RuntimeError(
            "Node.generate choice count did not match recorded origin events: "
            f"proxy calls {proxy.choice_call_count}, "
            f"observations {len(generate_context.observations)}."
        )
    session.node_generate_success_count += 1


def _classify_origin_admissions(node, observations):
    seen_rejected = False
    for observation in observations:
        admission = _classify_one_origin_admission(node, observation)
        observation.event.origin_admission = admission
        if seen_rejected:
            raise RuntimeError(
                "Node.generate recorded another origin choice after a rejected "
                f"admission at node {node.name}. Production breaks on rejection, "
                "so the rejected choice must be the last choice of the call."
            )
        if admission == ORIGIN_ADMISSION_REJECTED:
            seen_rejected = True


def _classify_one_origin_admission(node, observation):
    vehicle = observation.vehicle
    selected_link = observation.selected_link
    if vehicle.state == "run" and vehicle.link is selected_link:
        return ORIGIN_ADMISSION_ACCEPTED
    if vehicle.state == "wait" and _vehicle_is_in_generation_queue(node, vehicle):
        return ORIGIN_ADMISSION_REJECTED
    selected_name = _link_name(selected_link)
    current_name = _link_name(vehicle.link)
    raise RuntimeError(
        "Origin admission could not be classified for "
        f"vehicle {vehicle.name} at node {node.name}: "
        f"state {vehicle.state!r}, current link {current_name!r}, "
        f"selected link {selected_name!r}."
    )


# ---------------------------------------------------------------------------
# 9. Vehicle.route_next_link_choice wrapper
# ---------------------------------------------------------------------------


def diagnostic_route_next_link_choice(vehicle):
    """Record one in-trip method call on the real World.

    A call that reaches ``W.rng.choice`` once keeps the candidate list, ``p``,
    and selected Link captured inside the proxy. Those fields are not replaced
    after the production method returns.

    A call that does not reach ``choice`` is stored as a non-draw event and
    does not advance ``route_choice_ordinal``. Two or more ``choice`` calls
    inside one method are a diagnostic error after each original ``choice``
    has still been forwarded exactly once.
    """
    session = _require_active_session()
    world = vehicle.W
    if world is not session.real_world:
        session.virtual_route_choice_pass_count += 1
        called = 0
        session.original_route_next_link_choice(vehicle)
        called = 1
        _require_one_original_call(
            session,
            called,
            "virtual Vehicle.route_next_link_choice",
        )
        return

    session.real_route_choice_pass_count += 1
    _refuse_nested_context(session, "Vehicle.route_next_link_choice")
    original_generator = world.rng
    if original_generator is not session.original_generator:
        raise RuntimeError(
            "Real World rng is not the Generator captured when the diagnostic "
            "was installed."
        )
    if not isinstance(original_generator, np.random.Generator):
        raise RuntimeError(
            "Real World rng must be numpy.random.Generator before "
            "route_next_link_choice; "
            f"got {type(original_generator).__name__}."
        )

    current_link = vehicle.link
    if current_link is None:
        raise RuntimeError(
            f"Vehicle {vehicle.name} called route_next_link_choice without a link."
        )
    route_context = RouteNextLinkChoiceDiagnosticContext(
        vehicle=vehicle,
        vehicle_name=vehicle.name,
        current_link_name=_link_name(current_link),
        decision_node_name=current_link.end_node.name,
        decision_timestep=world.T,
        route_history_before=_route_history_before(vehicle),
        specified_route_used=vehicle.specified_route is not None,
        hard_deterministic_mode=bool(world.hard_deterministic_mode),
        links_prefer_names=_link_names_from_link_list(vehicle.links_prefer),
        links_avoid_names=_link_names_from_link_list(vehicle.links_avoid),
    )
    session.route_choice_context = route_context
    proxy = RouteChoiceDiagnosticRngProxy(session, original_generator)
    world.rng = proxy
    called = 0
    try:
        session.original_route_next_link_choice(vehicle)
        called = 1
    finally:
        _restore_temporary_generator(
            session,
            world,
            original_generator,
            "route",
            called == 1,
        )
    _require_one_original_call(session, called, "Vehicle.route_next_link_choice")
    _finish_route_next_link_choice_events(session, vehicle, route_context, proxy)
    session.route_choice_success_count += 1


def _finish_route_next_link_choice_events(session, vehicle, route_context, proxy):
    if proxy.choice_call_count == 1:
        return
    if proxy.choice_call_count == 0:
        _append_nondraw_route_choice_event(session, vehicle, route_context)
        return
    raise RuntimeError(
        "Vehicle.route_next_link_choice called W.rng.choice "
        f"{proxy.choice_call_count} times for vehicle {vehicle.name}; "
        "expected at most one."
    )


def _append_nondraw_route_choice_event(session, vehicle, route_context):
    """Store a call that did not draw. Do not allocate a draw ordinal."""
    selected_name = _link_name(vehicle.route_next_link)
    event = RouteChoiceRngDiagnosticEvent(
        run_method=session.run_method,
        world_kind=WORLD_KIND_REAL,
        event_kind=EVENT_KIND_IN_TRIP,
        vehicle_name=route_context.vehicle_name,
        route_choice_ordinal=None,
        attempt_ordinal_at_location=None,
        decision_timestep=route_context.decision_timestep,
        decision_node_name=route_context.decision_node_name,
        current_link_name=route_context.current_link_name,
        ordered_candidate_link_names=None,
        raw_preference_vector=None,
        normalized_probability_vector=None,
        probability_mode=None,
        rng_state_fingerprint_before=None,
        selected_link_name=selected_name,
        rng_state_fingerprint_after=None,
        specified_route_used=route_context.specified_route_used,
        hard_deterministic_mode=route_context.hard_deterministic_mode,
        links_prefer_names=route_context.links_prefer_names,
        links_avoid_names=route_context.links_avoid_names,
        choice_called=False,
        origin_admission=None,
        route_history_before=route_context.route_history_before,
        rng_state_canonical_json_before=None,
        rng_state_canonical_json_after=None,
        recomputed_normalized_probability_vector=None,
        provided_probability_matches_recomputed=None,
    )
    session.events.append(event)


# ---------------------------------------------------------------------------
# 10. Install and restore
# ---------------------------------------------------------------------------


def install_route_choice_rng_diagnostic(session):
    """Replace the two class methods and remember the original function objects.

    The caller must restore this session in ``finally``. There is no implicit
    context manager and no ``atexit`` hook. Only one session may be active.
    """
    global _ACTIVE_SESSION
    if not isinstance(session, RouteChoiceRngDiagnosticSession):
        raise RuntimeError(
            "install_route_choice_rng_diagnostic requires "
            "RouteChoiceRngDiagnosticSession; got "
            f"{type(session).__name__}."
        )
    if _ACTIVE_SESSION is not None or session.installed:
        raise RuntimeError(
            "A route-choice RNG diagnostic session is already installed."
        )
    if len(session.patches) != 0:
        raise RuntimeError("Diagnostic session already has saved patches.")
    if not isinstance(session.real_world.rng, np.random.Generator):
        raise RuntimeError(
            "real_world.rng must be numpy.random.Generator at install; got "
            f"{type(session.real_world.rng).__name__}."
        )

    import uxsim.uxsim as uxsim_module

    original_generate = uxsim_module.Node.generate
    original_route_choice = uxsim_module.Vehicle.route_next_link_choice
    session.original_generator = session.real_world.rng
    session.original_node_generate = original_generate
    session.original_route_next_link_choice = original_route_choice
    session.uxsim_module = uxsim_module

    session.patches.append((uxsim_module.Node, "generate", original_generate))
    uxsim_module.Node.generate = diagnostic_node_generate
    try:
        session.patches.append(
            (
                uxsim_module.Vehicle,
                "route_next_link_choice",
                original_route_choice,
            )
        )
        uxsim_module.Vehicle.route_next_link_choice = diagnostic_route_next_link_choice
    except BaseException:
        uxsim_module.Node.generate = original_generate
        session.patches.clear()
        session.original_generator = None
        session.original_node_generate = None
        session.original_route_next_link_choice = None
        session.uxsim_module = None
        raise

    _ACTIVE_SESSION = session
    session.installed = True


def restore_route_choice_rng_diagnostic(session):
    """Put the saved class methods back, last installed method first.

    Refuses to run when this session is not the active installed session.
    After restoration, both class methods must be the saved function objects
    by identity.
    """
    global _ACTIVE_SESSION
    if not isinstance(session, RouteChoiceRngDiagnosticSession):
        raise RuntimeError(
            "restore_route_choice_rng_diagnostic requires "
            "RouteChoiceRngDiagnosticSession; got "
            f"{type(session).__name__}."
        )
    if _ACTIVE_SESSION is None or session.installed is False:
        raise RuntimeError(
            "Route-choice RNG diagnostic is not installed. "
            "restore_route_choice_rng_diagnostic was called without an active session."
        )
    if session is not _ACTIVE_SESSION:
        raise RuntimeError(
            "restore_route_choice_rng_diagnostic received a session that is not "
            "the active session."
        )

    while len(session.patches) > 0:
        owner, attribute_name, original = session.patches.pop()
        setattr(owner, attribute_name, original)

    uxsim_module = session.uxsim_module
    if uxsim_module.Node.generate is not session.original_node_generate:
        raise RuntimeError(
            "Node.generate was not restored to the saved production method."
        )
    if (
        uxsim_module.Vehicle.route_next_link_choice
        is not session.original_route_next_link_choice
    ):
        raise RuntimeError(
            "Vehicle.route_next_link_choice was not restored to the saved "
            "production method."
        )

    _ACTIVE_SESSION = None
    session.installed = False


# ---------------------------------------------------------------------------
# 11. Validation after restore
# ---------------------------------------------------------------------------


def validate_restored_route_choice_rng_diagnostic(session):
    """Check the process and the event list after ``restore``.

    This does not simulate and does not write a file. It also does not prove
    that a diagnostic run matches a non-diagnostic run.
    """
    if not isinstance(session, RouteChoiceRngDiagnosticSession):
        raise RuntimeError(
            "validate_restored_route_choice_rng_diagnostic requires "
            "RouteChoiceRngDiagnosticSession; got "
            f"{type(session).__name__}."
        )
    if session.original_node_generate is None or session.original_route_next_link_choice is None:
        raise RuntimeError("Diagnostic session was never installed.")
    if session.installed:
        raise RuntimeError("Diagnostic class methods are still installed.")
    if _ACTIVE_SESSION is not None:
        raise RuntimeError("The module-level active diagnostic session is still set.")
    if len(session.patches) != 0:
        raise RuntimeError("Diagnostic patch list was not emptied by restore.")

    uxsim_module = session.uxsim_module
    if uxsim_module.Node.generate is not session.original_node_generate:
        raise RuntimeError("Node.generate does not match the saved method.")
    if (
        uxsim_module.Vehicle.route_next_link_choice
        is not session.original_route_next_link_choice
    ):
        raise RuntimeError(
            "Vehicle.route_next_link_choice does not match the saved method."
        )

    real_world = session.real_world
    if real_world.rng is not session.original_generator:
        raise RuntimeError(
            "real_world.rng is not the Generator object captured at install."
        )
    if not isinstance(real_world.rng, np.random.Generator):
        raise RuntimeError(
            "real_world.rng type is not numpy.random.Generator after restore."
        )
    if isinstance(real_world.rng, RouteChoiceDiagnosticRngProxy):
        raise RuntimeError("A diagnostic RNG proxy is still installed on the real World.")
    if session.generate_context is not None or session.route_choice_context is not None:
        raise RuntimeError("A diagnostic method context is still open.")
    if len(session.call_count_violation_messages) != 0:
        raise RuntimeError(
            "Original production method call count was not one on a normal return: "
            + "; ".join(session.call_count_violation_messages)
        )
    if len(session.generator_restore_failure_messages) != 0:
        raise RuntimeError(
            "World.rng was not restored to the original Generator: "
            + "; ".join(session.generator_restore_failure_messages)
        )
    if session.proxy_pickle_rejection_count != 0:
        raise RuntimeError(
            "Diagnostic RNG proxy was pickled or asked to pickle "
            f"{session.proxy_pickle_rejection_count} time(s)."
        )

    _validate_recorded_events(session)


def _validate_recorded_events(session):
    draw_ordinals_by_vehicle = {}
    attempt_ordinals_by_location = {}
    for event in session.events:
        if event.world_kind != WORLD_KIND_REAL:
            raise RuntimeError(
                "A non-real World event is in the real-World event list: "
                f"world_kind {event.world_kind!r}."
            )
        if event.run_method != session.run_method:
            raise RuntimeError(
                "Event run_method does not match the session: "
                f"{event.run_method!r}."
            )
        if event.choice_called:
            _validate_draw_event(event)
            if event.vehicle_name not in draw_ordinals_by_vehicle:
                draw_ordinals_by_vehicle[event.vehicle_name] = []
            draw_ordinals_by_vehicle[event.vehicle_name].append(
                event.route_choice_ordinal
            )
            location_key = decision_location_key(event)
            if location_key not in attempt_ordinals_by_location:
                attempt_ordinals_by_location[location_key] = []
            attempt_ordinals_by_location[location_key].append(
                event.attempt_ordinal_at_location
            )
            continue
        _validate_nondraw_event(event)

    for vehicle_name in draw_ordinals_by_vehicle:
        _require_contiguous_ordinals(
            draw_ordinals_by_vehicle[vehicle_name],
            f"route_choice_ordinal for vehicle {vehicle_name}",
        )
    for location_key in attempt_ordinals_by_location:
        _require_contiguous_ordinals(
            attempt_ordinals_by_location[location_key],
            f"attempt_ordinal_at_location for {location_key!r}",
        )


def _validate_draw_event(event):
    if event.route_choice_ordinal is None or event.attempt_ordinal_at_location is None:
        raise RuntimeError(
            f"Draw event for vehicle {event.vehicle_name} is missing an ordinal."
        )
    if event.rng_state_fingerprint_before is None or event.rng_state_fingerprint_after is None:
        raise RuntimeError(
            f"Draw event for vehicle {event.vehicle_name} is missing an RNG fingerprint."
        )
    if (
        event.rng_state_canonical_json_before is None
        or event.rng_state_canonical_json_after is None
    ):
        raise RuntimeError(
            f"Draw event for vehicle {event.vehicle_name} is missing canonical RNG JSON."
        )
    if event.selected_link_name is None:
        raise RuntimeError(
            f"Draw event for vehicle {event.vehicle_name} is missing the selected link."
        )
    if event.ordered_candidate_link_names is None:
        raise RuntimeError(
            f"Draw event for vehicle {event.vehicle_name} is missing candidate links."
        )
    if event.event_kind == EVENT_KIND_ORIGIN and event.origin_admission not in (
        ORIGIN_ADMISSION_ACCEPTED,
        ORIGIN_ADMISSION_REJECTED,
    ):
        raise RuntimeError(
            f"Origin draw for vehicle {event.vehicle_name} has origin_admission "
            f"{event.origin_admission!r}."
        )
    if event.event_kind == EVENT_KIND_IN_TRIP and event.origin_admission is not None:
        raise RuntimeError(
            f"In-trip draw for vehicle {event.vehicle_name} has an origin admission."
        )


def _validate_nondraw_event(event):
    if event.route_choice_ordinal is not None or event.attempt_ordinal_at_location is not None:
        raise RuntimeError(
            "A non-draw event advanced a draw or location ordinal for vehicle "
            f"{event.vehicle_name}."
        )
    if event.choice_called:
        raise RuntimeError(
            f"Non-draw validation saw choice_called for vehicle {event.vehicle_name}."
        )
    if event.rng_state_fingerprint_before is not None or event.rng_state_fingerprint_after is not None:
        raise RuntimeError(
            "A non-draw event contains an RNG fingerprint for vehicle "
            f"{event.vehicle_name}."
        )
    if event.ordered_candidate_link_names is not None or event.raw_preference_vector is not None:
        raise RuntimeError(
            "A non-draw event contains reconstructed choice inputs for vehicle "
            f"{event.vehicle_name}."
        )


def _require_contiguous_ordinals(ordinals, label):
    expected = 1
    for ordinal in ordinals:
        if ordinal != expected:
            raise RuntimeError(
                f"{label} has a gap or duplicate: saw {ordinal}, expected {expected}."
            )
        expected = expected + 1
