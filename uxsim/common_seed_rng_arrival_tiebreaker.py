"""Node visit numbers and arrival-tiebreaker keys.

A node visit number is how many times this vehicle has physically entered
links that end at that node. It is the sum of those link entry counts.
It is not an order-control visit id, and it is not stored as its own
counter.

This module does not decide that an arrival has happened, does not store
a tiebreaker, and does not draw from ``W.rng`` or ``W.order_control_rng``.
"""


# Fixed domain. Callers do not pass a free-form event name.
ARRIVAL_TIEBREAKER_DOMAIN = "arrival_tiebreaker"


def node_visit_number_from_link_entries(vehicle, node):
    """Sum this vehicle's entries on every link that ends at ``node``.

    ``node.inlinks`` is that set. A link that ends somewhere else is not
    added, even when its count is large. A missing count for an inlink is
    0. Zero stays 0. This function does not turn 0 into the first visit.
    The arrival recorder rejects a total below 1.

    Each stored count must be a non-negative ``int``. ``bool`` is not an
    int here. This function does not change the vehicle or the node.
    """
    total_entry_count = 0
    for inlink in node.inlinks.values():
        link_name = inlink.name
        if link_name in vehicle.link_entry_count_by_link_name:
            entry_count = vehicle.link_entry_count_by_link_name[link_name]
        else:
            entry_count = 0
        if isinstance(entry_count, bool) or type(entry_count) is not int or entry_count < 0:
            raise ValueError(
                f"Vehicle {vehicle.name} has link entry count {entry_count!r} "
                f"for link {link_name}, which ends at node {node.name}. "
                "A node visit number needs each count to be a non-negative "
                "int. bool, float, and str are not counts, and a negative "
                "count is not a visit."
            )
        total_entry_count = total_entry_count + entry_count
    return total_entry_count


def arrival_tiebreaker_key_parts(vehicle_name, node_name, node_visit_number):
    """Return ``(vehicle name, node name, node visit number)``.

    The inlink name, the timestep, the arrival time, and the
    order-control type are not part of the key. The same parts are used
    for the first visit and for a later visit. The visit number is what
    makes those events different.
    """
    return (vehicle_name, node_name, node_visit_number)
