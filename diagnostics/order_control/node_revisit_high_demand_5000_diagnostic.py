# DIAGNOSTIC SCRIPT — NOT a regression test.
#
# Phase 4-6N: Node revisit diagnostic — signalized UXsim vs FCFS vs BATCH on
# 5000-vehicle 6x6 grid. Investigates whether vehicles approach or pass the
# same node multiple times, and whether such revisits are BATCH-specific.
# Records pre–node-revisit-fix state.
#
# - Not part of the normal test suite; do not add to automated regression runs.
# - BATCH may exit with a known prefix violation at W.T=605; results up to that
#   point are still reported. That is intentional reproduction, not test failure.
# - Formal record: ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md §1G
#
# Run from the repository root:
#   python diagnostics/order_control/node_revisit_high_demand_5000_diagnostic.py
#
# Requires uxsim to be importable (e.g. pip install -e .).

import random
from collections import defaultdict

from uxsim import World

RANDOM_SEED = 0
DEMAND_GEN_SEED = 42
GRID_SIZE = 6
INTERNAL_GRID_NODE_COUNT = GRID_SIZE * GRID_SIZE
MIN_ELIGIBLE_NODES = 32
MIN_OD_MANHATTAN_DISTANCE = 5
SIGNAL_SETTING = [60, 60]
MERGE_PRIORITY = 1
NUMBER_OF_LANES = 1
INTERNAL_LINK_LENGTH = 400
OD_CONNECTOR_LENGTH = 300
FREE_FLOW_SPEED = 20
BATCH_SIZE = 10
BATCH_T_TRIGGER_LEVEL = 1
CLEARANCE_TIMESTEPS = 0

NUM_VEHICLES = 5000
DEPARTURE_START = 0
DEPARTURE_END = 500
TMAX = 30000
COMPARISON_T = 605
TARGET_VEHICLE = "veh_1619"
TARGET_NODE = "g_4_1"

MODE_LABELS = {
    "signalized_standard": "signalized UXsim (2-phase)",
    "fcfs": "FCFS (clearance=0)",
    "batch": "BATCH Level 1 (clearance=0, N=10)",
}


def _grid_node_name(row, column):
    return f"g_{row}_{column}"


def _external_od_node_names():
    names = []
    for column in range(GRID_SIZE):
        names.append(f"top_{column}")
        names.append(f"bottom_{column}")
    for row in range(GRID_SIZE):
        names.append(f"left_{row}")
        names.append(f"right_{row}")
    return names


def _od_to_grid_coord_map():
    mapping = {}
    for column in range(GRID_SIZE):
        mapping[f"top_{column}"] = (0, column)
        mapping[f"bottom_{column}"] = (GRID_SIZE - 1, column)
    for row in range(GRID_SIZE):
        mapping[f"left_{row}"] = (row, 0)
        mapping[f"right_{row}"] = (row, GRID_SIZE - 1)
    return mapping


OD_TO_GRID_COORD = _od_to_grid_coord_map()
EXTERNAL_OD_NODES = _external_od_node_names()


def _manhattan_distance(origin_coord, destination_coord):
    return abs(origin_coord[0] - destination_coord[0]) + abs(
        origin_coord[1] - destination_coord[1]
    )


def _generate_vehicle_plans(num_vehicles, departure_start, departure_end):
    rng = random.Random(DEMAND_GEN_SEED)
    plans = []
    vehicle_index = 0
    while len(plans) < num_vehicles:
        origin = rng.choice(EXTERNAL_OD_NODES)
        destination = rng.choice(EXTERNAL_OD_NODES)
        if origin == destination:
            continue
        origin_grid_coord = OD_TO_GRID_COORD[origin]
        destination_grid_coord = OD_TO_GRID_COORD[destination]
        manhattan_distance = _manhattan_distance(
            origin_grid_coord, destination_grid_coord
        )
        if manhattan_distance < MIN_OD_MANHATTAN_DISTANCE:
            continue
        departure_time = departure_start + (departure_end - departure_start) * len(
            plans
        ) / max(num_vehicles - 1, 1)
        plans.append(
            {
                "origin": origin,
                "destination": destination,
                "departure_time": departure_time,
                "name": f"veh_{vehicle_index}",
            }
        )
        vehicle_index += 1
    return plans


def _add_grid_network(W, control_mode):
    spacing = 1.0
    signalize_internal = control_mode == "signalized_standard"

    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE):
            node_name = _grid_node_name(row, column)
            if signalize_internal:
                W.addNode(
                    node_name,
                    column * spacing,
                    -row * spacing,
                    signal=SIGNAL_SETTING,
                )
            else:
                W.addNode(node_name, column * spacing, -row * spacing)

    for column in range(GRID_SIZE):
        W.addNode(f"top_{column}", column * spacing, spacing)
        W.addNode(
            f"bottom_{column}",
            column * spacing,
            -GRID_SIZE * spacing,
        )

    for row in range(GRID_SIZE):
        W.addNode(f"left_{row}", -spacing, -row * spacing)
        W.addNode(
            f"right_{row}",
            GRID_SIZE * spacing,
            -row * spacing,
        )

    def add_link(link_name, start_node, end_node, length, signal_group):
        W.addLink(
            link_name,
            start_node,
            end_node,
            length=length,
            free_flow_speed=FREE_FLOW_SPEED,
            number_of_lanes=NUMBER_OF_LANES,
            merge_priority=MERGE_PRIORITY,
            signal_group=signal_group,
        )

    for row in range(GRID_SIZE):
        for column in range(GRID_SIZE - 1):
            left_node = _grid_node_name(row, column)
            right_node = _grid_node_name(row, column + 1)
            add_link(
                f"h_{row}_{column}_{column + 1}",
                left_node,
                right_node,
                INTERNAL_LINK_LENGTH,
                signal_group=0,
            )
            add_link(
                f"h_{row}_{column + 1}_{column}",
                right_node,
                left_node,
                INTERNAL_LINK_LENGTH,
                signal_group=0,
            )

    for row in range(GRID_SIZE - 1):
        for column in range(GRID_SIZE):
            upper_node = _grid_node_name(row, column)
            lower_node = _grid_node_name(row + 1, column)
            add_link(
                f"v_{row}_{row + 1}_{column}",
                upper_node,
                lower_node,
                INTERNAL_LINK_LENGTH,
                signal_group=1,
            )
            add_link(
                f"v_{row + 1}_{row}_{column}",
                lower_node,
                upper_node,
                INTERNAL_LINK_LENGTH,
                signal_group=1,
            )

    for column in range(GRID_SIZE):
        add_link(
            f"top_{column}_to_g_0_{column}",
            f"top_{column}",
            _grid_node_name(0, column),
            OD_CONNECTOR_LENGTH,
            signal_group=1,
        )
        add_link(
            f"g_0_{column}_to_top_{column}",
            _grid_node_name(0, column),
            f"top_{column}",
            OD_CONNECTOR_LENGTH,
            signal_group=1,
        )
        add_link(
            f"bottom_{column}_to_g_5_{column}",
            f"bottom_{column}",
            _grid_node_name(GRID_SIZE - 1, column),
            OD_CONNECTOR_LENGTH,
            signal_group=1,
        )
        add_link(
            f"g_5_{column}_to_bottom_{column}",
            _grid_node_name(GRID_SIZE - 1, column),
            f"bottom_{column}",
            OD_CONNECTOR_LENGTH,
            signal_group=1,
        )

    for row in range(GRID_SIZE):
        add_link(
            f"left_{row}_to_g_{row}_0",
            f"left_{row}",
            _grid_node_name(row, 0),
            OD_CONNECTOR_LENGTH,
            signal_group=0,
        )
        add_link(
            f"g_{row}_0_to_left_{row}",
            _grid_node_name(row, 0),
            f"left_{row}",
            OD_CONNECTOR_LENGTH,
            signal_group=0,
        )
        add_link(
            f"right_{row}_to_g_{row}_5",
            f"right_{row}",
            _grid_node_name(row, GRID_SIZE - 1),
            OD_CONNECTOR_LENGTH,
            signal_group=0,
        )
        add_link(
            f"g_{row}_5_to_right_{row}",
            _grid_node_name(row, GRID_SIZE - 1),
            f"right_{row}",
            OD_CONNECTOR_LENGTH,
            signal_group=0,
        )


def _add_vehicles(W, vehicle_plans):
    for plan in vehicle_plans:
        W.addVehicle(
            plan["origin"],
            plan["destination"],
            plan["departure_time"],
            name=plan["name"],
        )


def _eligible_node_names(W):
    return [node.name for node in W.NODES if node.order_control_eligible]


def setup_world(control_mode, vehicle_plans, tmax):
    W = World(
        name=f"node_revisit_diagnostic_{control_mode}",
        deltan=1,
        tmax=tmax,
        print_mode=0,
        save_mode=0,
        show_mode=0,
        random_seed=RANDOM_SEED,
    )
    _add_grid_network(W, control_mode)
    _add_vehicles(W, vehicle_plans)

    if control_mode == "fcfs":
        W.infer_order_control_eligible_nodes()
        W.set_order_control_clearance_timesteps(CLEARANCE_TIMESTEPS)
        eligible_node_names = _eligible_node_names(W)
        assert len(eligible_node_names) >= MIN_ELIGIBLE_NODES
        W.set_order_control_for_nodes(
            eligible_node_names,
            order_control_type="fcfs",
        )
    elif control_mode == "batch":
        W.infer_order_control_eligible_nodes()
        W.set_order_control_clearance_timesteps(CLEARANCE_TIMESTEPS)
        eligible_node_names = _eligible_node_names(W)
        assert len(eligible_node_names) >= MIN_ELIGIBLE_NODES
        W.set_order_control_for_nodes(
            eligible_node_names,
            order_control_type="batch",
            batch_size=BATCH_SIZE,
            order_control_batch_t_trigger_level=BATCH_T_TRIGGER_LEVEL,
        )
    elif control_mode != "signalized_standard":
        raise ValueError(f"unsupported control_mode: {control_mode!r}")

    W.finalize_scenario()
    return W


class NodeRevisitTracker:
    def __init__(self):
        self.approach_events = []
        self.passage_events = []
        self.reapproach_events = []
        self.repassage_events = []
        self.prev_links = {}
        self.approach_count = defaultdict(int)
        self.passage_count = defaultdict(int)
        self.link_entry_sequence = defaultdict(list)
        self.approach_sequence = defaultdict(list)
        self.passage_sequence = defaultdict(list)

    def _vehicle_names(self, W):
        return set(self.prev_links) | set(W.VEHICLES_LIVING)

    def snapshot_before_step(self, W):
        self.prev_links = {}
        for name in W.VEHICLES_LIVING:
            self.prev_links[name] = W.VEHICLES_LIVING[name].link

    def observe_after_step(self, W):
        timestep = W.T
        for name in self._vehicle_names(W):
            veh = W.VEHICLES.get(name)
            if veh is None:
                continue
            prev_link = self.prev_links.get(name)
            curr_link = veh.link
            if prev_link is curr_link:
                continue

            if curr_link is not None:
                node = curr_link.end_node
                key = (name, node.name)
                self.approach_count[key] += 1
                approach_number = self.approach_count[key]
                event = {
                    "timestep": timestep,
                    "vehicle": name,
                    "node": node.name,
                    "link": curr_link.name,
                    "approach_number": approach_number,
                }
                self.approach_events.append(event)
                self.approach_sequence[name].append(
                    (timestep, node.name, curr_link.name)
                )
                self.link_entry_sequence[name].append((timestep, curr_link.name))

                if approach_number >= 2:
                    first = next(
                        e
                        for e in self.approach_events
                        if e["vehicle"] == name and e["node"] == node.name
                    )
                    between_links = [
                        link
                        for ts, link in self.link_entry_sequence[name]
                        if first["timestep"] < ts < timestep
                    ]
                    between_nodes = [
                        node_name
                        for ts, node_name, _ in self.approach_sequence[name]
                        if first["timestep"] < ts < timestep
                    ]
                    self.reapproach_events.append(
                        {
                            "vehicle": name,
                            "node": node.name,
                            "first_timestep": first["timestep"],
                            "first_link": first["link"],
                            "second_timestep": timestep,
                            "second_link": curr_link.name,
                            "approach_number": approach_number,
                            "links_between": between_links,
                            "nodes_between": between_nodes,
                        }
                    )

            if (
                prev_link is not None
                and curr_link is not None
                and prev_link is not curr_link
                and prev_link.end_node is curr_link.start_node
            ):
                node = prev_link.end_node
                key = (name, node.name)
                self.passage_count[key] += 1
                passage_number = self.passage_count[key]
                event = {
                    "timestep": timestep,
                    "vehicle": name,
                    "node": node.name,
                    "inlink": prev_link.name,
                    "outlink": curr_link.name,
                    "passage_number": passage_number,
                }
                self.passage_events.append(event)
                self.passage_sequence[name].append(
                    (timestep, node.name, prev_link.name, curr_link.name)
                )

                if passage_number >= 2:
                    first = next(
                        e
                        for e in self.passage_events
                        if e["vehicle"] == name and e["node"] == node.name
                    )
                    between_links = [
                        link
                        for ts, link in self.link_entry_sequence[name]
                        if first["timestep"] < ts < timestep
                    ]
                    between_nodes = [
                        node_name
                        for ts, node_name, _ in self.approach_sequence[name]
                        if first["timestep"] < ts < timestep
                    ]
                    self.repassage_events.append(
                        {
                            "vehicle": name,
                            "node": node.name,
                            "first_timestep": first["timestep"],
                            "first_inlink": first["inlink"],
                            "first_outlink": first["outlink"],
                            "second_timestep": timestep,
                            "second_inlink": prev_link.name,
                            "second_outlink": curr_link.name,
                            "passage_number": passage_number,
                            "links_between": between_links,
                            "nodes_between": between_nodes,
                        }
                    )

            self.prev_links[name] = curr_link

    def aggregate(self, max_timestep=None):
        approach_events = self.approach_events
        passage_events = self.passage_events
        reapproach_events = self.reapproach_events
        repassage_events = self.repassage_events

        if max_timestep is not None:
            approach_events = [
                e for e in approach_events if e["timestep"] <= max_timestep
            ]
            passage_events = [
                e for e in passage_events if e["timestep"] <= max_timestep
            ]
            reapproach_events = [
                e for e in reapproach_events if e["second_timestep"] <= max_timestep
            ]
            repassage_events = [
                e for e in repassage_events if e["second_timestep"] <= max_timestep
            ]

        vehicles_with_approach = {e["vehicle"] for e in approach_events}
        vehicles_with_reapproach = {e["vehicle"] for e in reapproach_events}
        nodes_with_reapproach = {e["node"] for e in reapproach_events}

        vehicles_with_passage = {e["vehicle"] for e in passage_events}
        vehicles_with_repassage = {e["vehicle"] for e in repassage_events}
        nodes_with_repassage = {e["node"] for e in repassage_events}

        max_approach = 0
        for (veh, node), count in self.approach_count.items():
            if max_timestep is not None:
                count = sum(
                    1
                    for e in self.approach_events
                    if e["vehicle"] == veh
                    and e["node"] == node
                    and e["timestep"] <= max_timestep
                )
            max_approach = max(max_approach, count)

        max_passage = 0
        for (veh, node), count in self.passage_count.items():
            if max_timestep is not None:
                count = sum(
                    1
                    for e in self.passage_events
                    if e["vehicle"] == veh
                    and e["node"] == node
                    and e["timestep"] <= max_timestep
                )
            max_passage = max(max_passage, count)

        total_vehicles_observed = len(
            {name for name in self.prev_links}
            | {e["vehicle"] for e in self.approach_events}
        )

        return {
            "max_timestep": max_timestep,
            "total_vehicles_observed": total_vehicles_observed,
            "vehicles_with_approach": len(vehicles_with_approach),
            "vehicles_with_reapproach": len(vehicles_with_reapproach),
            "reapproach_vehicle_ratio": (
                len(vehicles_with_reapproach) / len(vehicles_with_approach)
                if vehicles_with_approach
                else 0.0
            ),
            "reapproach_event_count": len(reapproach_events),
            "nodes_with_reapproach": len(nodes_with_reapproach),
            "max_approach_count": max_approach,
            "vehicles_with_passage": len(vehicles_with_passage),
            "vehicles_with_repassage": len(vehicles_with_repassage),
            "repassage_vehicle_ratio": (
                len(vehicles_with_repassage) / len(vehicles_with_passage)
                if vehicles_with_passage
                else 0.0
            ),
            "repassage_event_count": len(repassage_events),
            "nodes_with_repassage": len(nodes_with_repassage),
            "max_passage_count": max_passage,
            "reapproach_examples": reapproach_events[:10],
            "repassage_examples": repassage_events[:10],
        }

    def vehicle_summary(self, vehicle_name, max_timestep=None):
        link_entries = self.link_entry_sequence[vehicle_name]
        approaches = self.approach_sequence[vehicle_name]
        passages = self.passage_sequence[vehicle_name]

        if max_timestep is not None:
            link_entries = [(t, l) for t, l in link_entries if t <= max_timestep]
            approaches = [(t, n, l) for t, n, l in approaches if t <= max_timestep]
            passages = [
                (t, n, il, ol) for t, n, il, ol in passages if t <= max_timestep
            ]

        target_approaches = [
            (t, link) for t, node, link in approaches if node == TARGET_NODE
        ]
        target_passages = [
            (t, inlink, outlink)
            for t, node, inlink, outlink in passages
            if node == TARGET_NODE
        ]

        return {
            "link_entries": link_entries,
            "approaches": approaches,
            "passages": passages,
            "target_node_approach_count": len(target_approaches),
            "target_node_passage_count": len(target_passages),
            "target_node_approach_timesteps": [t for t, _ in target_approaches],
            "target_node_approach_links": [l for _, l in target_approaches],
            "target_node_passage_timesteps": [t for t, _, _ in target_passages],
            "target_node_passage_details": target_passages,
            "target_node_reapproached": len(target_approaches) >= 2,
            "target_node_repassed": len(target_passages) >= 2,
        }


def run_timestep_simulation(W, tracker, stop_on_exception=False):
    exception_info = None
    while W.T < W.TSIZE:
        tracker.snapshot_before_step(W)
        try:
            W.exec_simulation(duration_t2=W.DELTAT)
        except ValueError as exc:
            tracker.observe_after_step(W)
            exception_info = {
                "type": type(exc).__name__,
                "message": str(exc),
                "timestep": W.T,
            }
            if stop_on_exception:
                break
            raise
        tracker.observe_after_step(W)
        if W.T >= W.TSIZE:
            break
    return exception_info


def _print_aggregate(label, agg):
    period = (
        f"timestep <= {agg['max_timestep']}"
        if agg["max_timestep"] is not None
        else "full simulation"
    )
    print(f"\n--- {label} ({period}) ---")
    print(f"  vehicles with >=1 node approach: {agg['vehicles_with_approach']}")
    print(
        f"  vehicles with >=1 re-approach: {agg['vehicles_with_reapproach']} "
        f"({agg['reapproach_vehicle_ratio']:.4f} of approach vehicles)"
    )
    print(f"  re-approach events: {agg['reapproach_event_count']}")
    print(f"  nodes re-approached: {agg['nodes_with_reapproach']}")
    print(f"  max approach count (1 vehicle, 1 node): {agg['max_approach_count']}")
    print(f"  vehicles with >=1 node passage: {agg['vehicles_with_passage']}")
    print(
        f"  vehicles with >=1 re-passage: {agg['vehicles_with_repassage']} "
        f"({agg['repassage_vehicle_ratio']:.4f} of passage vehicles)"
    )
    print(f"  re-passage events: {agg['repassage_event_count']}")
    print(f"  nodes re-passed: {agg['nodes_with_repassage']}")
    print(f"  max passage count (1 vehicle, 1 node): {agg['max_passage_count']}")


def _print_examples(title, examples, kind):
    print(f"\n{title} (up to 10):")
    if not examples:
        print("  (none)")
        return
    for index, ex in enumerate(examples, 1):
        print(f"  [{index}] vehicle={ex['vehicle']} node={ex['node']}")
        if kind == "reapproach":
            print(
                f"      1st: T={ex['first_timestep']} inlink={ex['first_link']}"
            )
            print(
                f"      2nd: T={ex['second_timestep']} inlink={ex['second_link']} "
                f"(approach #{ex['approach_number']})"
            )
        else:
            print(
                f"      1st: T={ex['first_timestep']} "
                f"{ex['first_inlink']} -> {ex['first_outlink']}"
            )
            print(
                f"      2nd: T={ex['second_timestep']} "
                f"{ex['second_inlink']} -> {ex['second_outlink']} "
                f"(passage #{ex['passage_number']})"
            )
        print(f"      links between: {ex['links_between']}")
        print(f"      nodes between: {ex['nodes_between']}")


def _print_vehicle_summary(mode_label, summary, max_timestep=None):
    period = (
        f"T<={max_timestep}" if max_timestep is not None else "full simulation"
    )
    print(f"\n--- {TARGET_VEHICLE} in {mode_label} ({period}) ---")
    print(f"  link entry count: {len(summary['link_entries'])}")
    print(f"  node approach count: {len(summary['approaches'])}")
    print(f"  node passage count: {len(summary['passages'])}")
    print(
        f"  {TARGET_NODE} approaches: {summary['target_node_approach_count']} "
        f"at T={summary['target_node_approach_timesteps']}"
    )
    print(f"  {TARGET_NODE} approach inlinks: {summary['target_node_approach_links']}")
    print(
        f"  {TARGET_NODE} passages: {summary['target_node_passage_count']} "
        f"at T={summary['target_node_passage_timesteps']}"
    )
    for t, inlink, outlink in summary["target_node_passage_details"]:
        print(f"    T={t}: {inlink} -> {outlink}")
    print(f"  {TARGET_NODE} re-approached: {summary['target_node_reapproached']}")
    print(f"  {TARGET_NODE} re-passed: {summary['target_node_repassed']}")
    if summary["link_entries"]:
        tail = summary["link_entries"][-15:]
        print(f"  last link entries: {tail}")


def run_node_revisit_diagnostic():
    vehicle_plans = _generate_vehicle_plans(
        NUM_VEHICLES, DEPARTURE_START, DEPARTURE_END
    )

    results = {}
    batch_exception = None

    print("=" * 72)
    print("Node Revisit Diagnostic: 5000 vehicles, clearance=0, 6x6 grid")
    print("=" * 72)
    print(f"vehicle plans: {len(vehicle_plans)} vehicles, seed={DEMAND_GEN_SEED}")
    print(f"comparison timestep: {COMPARISON_T}")

    for control_mode in ("signalized_standard", "fcfs", "batch"):
        print(f"\n{'=' * 72}")
        print(f"Running: {MODE_LABELS[control_mode]}")
        print("=" * 72)

        W = setup_world(control_mode, vehicle_plans, TMAX)
        tracker = NodeRevisitTracker()
        stop_on_exception = control_mode == "batch"
        exception_info = run_timestep_simulation(
            W, tracker, stop_on_exception=stop_on_exception
        )

        if exception_info is not None:
            batch_exception = exception_info
            print(
                f"\nBATCH stopped with {exception_info['type']} at T={exception_info['timestep']}:"
            )
            print(f"  {exception_info['message']}")

        results[control_mode] = {
            "tracker": tracker,
            "exception": exception_info,
            "final_T": W.T,
        }

    print("\n" + "=" * 72)
    print("AGGREGATE RESULTS")
    print("=" * 72)

    aggregates_605 = {}
    aggregates_full = {}

    for control_mode in ("signalized_standard", "fcfs", "batch"):
        tracker = results[control_mode]["tracker"]
        aggregates_605[control_mode] = tracker.aggregate(max_timestep=COMPARISON_T)
        if control_mode != "batch":
            aggregates_full[control_mode] = tracker.aggregate(max_timestep=None)
        else:
            aggregates_full[control_mode] = None

        _print_aggregate(MODE_LABELS[control_mode], aggregates_605[control_mode])
        if aggregates_full[control_mode] is not None:
            _print_aggregate(
                MODE_LABELS[control_mode] + " [full run]",
                aggregates_full[control_mode],
            )

    for control_mode in ("signalized_standard", "fcfs", "batch"):
        agg = aggregates_605[control_mode]
        _print_examples(
            f"{MODE_LABELS[control_mode]} first re-approach examples (T<={COMPARISON_T})",
            agg["reapproach_examples"],
            "reapproach",
        )
        _print_examples(
            f"{MODE_LABELS[control_mode]} first re-passage examples (T<={COMPARISON_T})",
            agg["repassage_examples"],
            "repassage",
        )

    print("\n" + "=" * 72)
    print(f"{TARGET_VEHICLE} COMPARISON")
    print("=" * 72)

    veh_summaries_605 = {}
    veh_summaries_full = {}
    for control_mode in ("signalized_standard", "fcfs", "batch"):
        tracker = results[control_mode]["tracker"]
        veh_summaries_605[control_mode] = tracker.vehicle_summary(
            TARGET_VEHICLE, max_timestep=COMPARISON_T
        )
        if control_mode != "batch":
            veh_summaries_full[control_mode] = tracker.vehicle_summary(
                TARGET_VEHICLE, max_timestep=None
            )
        else:
            veh_summaries_full[control_mode] = veh_summaries_605[control_mode]

        _print_vehicle_summary(
            MODE_LABELS[control_mode],
            veh_summaries_605[control_mode],
            max_timestep=COMPARISON_T,
        )

    print("\n" + "=" * 72)
    print("INTERPRETATION")
    print("=" * 72)

    sig_reapproach = aggregates_605["signalized_standard"]["vehicles_with_reapproach"]
    fcfs_reapproach = aggregates_605["fcfs"]["vehicles_with_reapproach"]
    batch_reapproach = aggregates_605["batch"]["vehicles_with_reapproach"]

    print(
        f"- signalized UXsim: re-approach vehicles (T<={COMPARISON_T}): {sig_reapproach}"
    )
    print(f"- FCFS: re-approach vehicles (T<={COMPARISON_T}): {fcfs_reapproach}")
    print(f"- BATCH: re-approach vehicles (T<={COMPARISON_T}): {batch_reapproach}")

    if sig_reapproach > 0 and fcfs_reapproach > 0 and batch_reapproach > 0:
        print(
            "- All three modes show node re-approach: re-visits are NOT BATCH-specific."
        )
        print(
            "- BATCH prefix violation is likely a state-management issue "
            "(stale assignment), not re-visit occurrence itself."
        )
    elif batch_reapproach > 0 and sig_reapproach == 0 and fcfs_reapproach == 0:
        print(
            "- Re-approach only in BATCH at T<=605; traffic-state difference may matter."
        )
    else:
        print("- Mixed pattern; see per-mode counts above.")

    print(
        f"- veh_1619 g_4_1 re-approach: "
        f"signalized={veh_summaries_605['signalized_standard']['target_node_reapproached']}, "
        f"FCFS={veh_summaries_605['fcfs']['target_node_reapproached']}, "
        f"BATCH={veh_summaries_605['batch']['target_node_reapproached']}"
    )

    if batch_exception is not None:
        print(
            f"\nBATCH ended with exception at T={batch_exception['timestep']} "
            "(results above include history up to that point)."
        )
        raise ValueError(batch_exception["message"])

    return {
        "aggregates_605": aggregates_605,
        "aggregates_full": aggregates_full,
        "veh_summaries_605": veh_summaries_605,
        "batch_exception": batch_exception,
    }


if __name__ == "__main__":
    run_node_revisit_diagnostic()
