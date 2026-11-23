"""Category selection for origin and in-trip route choice.

This module does not read a World, does not advance an attempt counter,
and does not draw from ``W.rng`` or ``W.order_control_rng``. The caller
builds the research key, asks the pure keyed helper for one uniform
value, and only then increments the attempt that belongs to that event.

Origin and in-trip are different research events. They do not share a
domain with each other, with arrival tiebreakers, or with ordinary merge.
"""

import math


# Fixed domains. Callers do not pass a free-form event name, so a typo
# cannot silently create a third route-choice family.
ORIGIN_ROUTE_CHOICE_DOMAIN = "origin_route_choice"
IN_TRIP_ROUTE_CHOICE_DOMAIN = "in_trip_route_choice"


def select_route_choice_candidate(candidate_links, preference_weights, uniform_value):
    """Pick one link from an already filtered candidate list.

    The candidate order is the order the caller supplies. This function
    does not sort, copy link objects, or change Vehicle or World state.

    Zero candidates are not a successful choice. One candidate is that
    link, with no use of ``uniform_value``. Two or more candidates use
    ``uniform_value`` in ``[0, 1)``.

    A positive preference total uses those weights as category
    probabilities, in candidate order. The first candidate whose
    cumulative probability is strictly greater than ``uniform_value`` is
    chosen. If floating-point rounding never crosses the value, the last
    candidate is the explicit remainder. That remainder is only for a
    positive total. It does not turn an empty list into a choice.

    A total of zero with two or more candidates is an equal-category
    draw, still one probabilistic choice. Negative, NaN, or other
    non-finite weights are rejected before any index is chosen.
    """
    candidates = []
    for candidate_link in candidate_links:
        candidates.append(candidate_link)
    candidate_count = len(candidates)
    if candidate_count == 0:
        raise ValueError(
            "Route choice has no candidate link. No uniform value is "
            "applied. An empty candidate list is not a successful choice."
        )
    if candidate_count == 1:
        return candidates[0]

    weights = _preference_weights(preference_weights, candidate_count)
    checked_uniform = _require_unit_interval_uniform(uniform_value)

    total_weight = 0.0
    for weight in weights:
        total_weight += weight

    if total_weight > 0.0:
        cumulative_probability = 0.0
        for index, weight in enumerate(weights):
            cumulative_probability += weight / total_weight
            if checked_uniform < cumulative_probability:
                return candidates[index]
        return candidates[-1]

    equal_slot = checked_uniform * candidate_count
    equal_index = int(equal_slot)
    if equal_index >= candidate_count:
        equal_index = candidate_count - 1
    if equal_index < 0:
        equal_index = 0
    return candidates[equal_index]


def _preference_weights(preference_weights, candidate_count):
    """Copy weights into plain floats and reject values that are not weights."""
    weights = []
    for preference_weight in preference_weights:
        if isinstance(preference_weight, bool):
            raise ValueError(
                "Route choice preference must be a finite non-negative "
                f"number, not bool {preference_weight!r}."
            )
        try:
            weight = float(preference_weight)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Route choice preference must be a finite non-negative "
                f"number. Got {preference_weight!r}."
            ) from error
        if not math.isfinite(weight) or weight < 0.0:
            raise ValueError(
                "Route choice preference must be a finite non-negative "
                f"number. Got {preference_weight!r}."
            )
        weights.append(weight)
    if len(weights) != candidate_count:
        raise ValueError(
            "Route choice preference count does not match the candidate "
            f"count. preferences={len(weights)}, candidates={candidate_count}."
        )
    return weights


def _require_unit_interval_uniform(uniform_value):
    """Accept one ``[0, 1)`` float. Do not treat bool as a draw."""
    if isinstance(uniform_value, bool) or type(uniform_value) is not float:
        raise ValueError(
            "Route choice uniform value must be a float in [0, 1). "
            f"Got type {type(uniform_value).__name__} value {uniform_value!r}."
        )
    if math.isnan(uniform_value) or uniform_value < 0.0 or uniform_value >= 1.0:
        raise ValueError(
            "Route choice uniform value must be in [0, 1). "
            f"Got {uniform_value!r}."
        )
    return uniform_value
