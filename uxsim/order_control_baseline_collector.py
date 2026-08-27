"""
Collector for snapshot-fixed order-control baseline visit records.

Stores plain arrival and passage timesteps for TVT global-World baseline research.
Institutional logic (decision window, right_of_entry_vehicle, trade_rank) stays outside.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(
            f"{field_name} must be a non-empty str; got {value!r}."
        )
    return value


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a bool; got {value!r}.")
    return value


def _require_positive_int(value: Any, field_name: str) -> int:
    # bool is a subclass of int in Python, so exclude it explicitly.
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(
            f"{field_name} must be a positive int (not bool); got {value!r}."
        )
    return value


def _require_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"{field_name} must be a non-negative int (not bool); got {value!r}."
        )
    return value


def _require_timestep(value: Any, field_name: str) -> int:
    return _require_non_negative_int(value, field_name)


def _require_arrival_tiebreaker(value: Any, field_name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"{field_name} must be an int or float (not bool); got {value!r}."
        )
    return value


def _require_route_next_link_name(value: Any, field_name: str) -> str:
    return _require_non_empty_str(value, field_name)


@dataclass
class OrderControlBaselineVisitRecord:
    """One snapshot-fixed visit and its baseline arrival/passage facts."""

    vehicle_name: str
    vehicle_id: int
    node_name: str
    inlink_name: str
    visit_id: int
    was_arrived_at_snapshot: bool
    baseline_arrival_timestep: int | None
    arrival_tiebreaker: int | float | None
    route_next_link_name: str | None
    baseline_passage_timestep: int | None


class OrderControlBaselineCollector:
    """
    Holds snapshot-fixed visit records for one fork baseline run.

    Does not hold a reference back to the fork World.
    """

    def __init__(self) -> None:
        self._visit_records_by_primary_key: dict[
            tuple[str, int], OrderControlBaselineVisitRecord
        ] = {}
        self._visit_record_by_vehicle_name: dict[
            str, OrderControlBaselineVisitRecord
        ] = {}
        self._visit_records_by_node_name: dict[
            str, list[OrderControlBaselineVisitRecord]
        ] = {}

    def register_snapshot_visit(
        self,
        *,
        vehicle_name: str,
        vehicle_id: int,
        node_name: str,
        inlink_name: str,
        visit_id: int,
        was_arrived_at_snapshot: bool,
        baseline_arrival_timestep: int | None,
        arrival_tiebreaker: int | float | None,
        route_next_link_name: str | None,
        baseline_passage_timestep: int | None,
    ) -> None:
        """
        Register one snapshot-fixed visit and build index entries.

        Driver-side UXsim state checks are intentionally omitted here.
        """
        vehicle_name = _require_non_empty_str(vehicle_name, "vehicle_name")
        vehicle_id = _require_non_negative_int(vehicle_id, "vehicle_id")
        node_name = _require_non_empty_str(node_name, "node_name")
        inlink_name = _require_non_empty_str(inlink_name, "inlink_name")
        visit_id = _require_positive_int(visit_id, "visit_id")
        was_arrived_at_snapshot = _require_bool(
            was_arrived_at_snapshot, "was_arrived_at_snapshot"
        )

        primary_key = (vehicle_name, visit_id)
        if primary_key in self._visit_records_by_primary_key:
            raise ValueError(
                f"Duplicate snapshot visit primary key "
                f"(vehicle_name={vehicle_name!r}, visit_id={visit_id})."
            )
        if vehicle_name in self._visit_record_by_vehicle_name:
            existing_visit_id = self._visit_record_by_vehicle_name[
                vehicle_name
            ].visit_id
            raise ValueError(
                f"Vehicle {vehicle_name!r} is already registered with "
                f"visit_id={existing_visit_id}; cannot register visit_id={visit_id}."
            )

        if baseline_passage_timestep is not None:
            raise ValueError(
                "baseline_passage_timestep must be None at snapshot registration."
            )

        if was_arrived_at_snapshot:
            baseline_arrival_timestep = _require_timestep(
                baseline_arrival_timestep, "baseline_arrival_timestep"
            )
            arrival_tiebreaker = _require_arrival_tiebreaker(
                arrival_tiebreaker, "arrival_tiebreaker"
            )
            route_next_link_name = _require_route_next_link_name(
                route_next_link_name, "route_next_link_name"
            )
        else:
            if baseline_arrival_timestep is not None:
                raise ValueError(
                    "baseline_arrival_timestep must be None for a not-yet-arrived "
                    "snapshot visit (was_arrived_at_snapshot=False)."
                )
            if arrival_tiebreaker is not None:
                raise ValueError(
                    "arrival_tiebreaker must be None for a not-yet-arrived "
                    "snapshot visit (was_arrived_at_snapshot=False)."
                )
            if route_next_link_name is not None:
                raise ValueError(
                    "route_next_link_name must be None for a not-yet-arrived "
                    "snapshot visit (was_arrived_at_snapshot=False)."
                )

        record = OrderControlBaselineVisitRecord(
            vehicle_name=vehicle_name,
            vehicle_id=vehicle_id,
            node_name=node_name,
            inlink_name=inlink_name,
            visit_id=visit_id,
            was_arrived_at_snapshot=was_arrived_at_snapshot,
            baseline_arrival_timestep=baseline_arrival_timestep,
            arrival_tiebreaker=arrival_tiebreaker,
            route_next_link_name=route_next_link_name,
            baseline_passage_timestep=None,
        )

        self._visit_records_by_primary_key[primary_key] = record
        self._visit_record_by_vehicle_name[vehicle_name] = record
        node_records = self._visit_records_by_node_name.setdefault(node_name, [])
        node_records.append(record)

    def record_baseline_arrival(
        self,
        *,
        vehicle_name: str,
        visit_id: int,
        node_name: str,
        baseline_arrival_timestep: int,
        arrival_tiebreaker: int | float,
        route_next_link_name: str,
    ) -> None:
        """
        Record baseline arrival facts for a not-yet-arrived snapshot visit (B).

        Visits outside the snapshot-fixed set are ignored without error.
        """
        vehicle_name = _require_non_empty_str(vehicle_name, "vehicle_name")
        visit_id = _require_positive_int(visit_id, "visit_id")

        primary_key = (vehicle_name, visit_id)
        record = self._visit_records_by_primary_key.get(primary_key)
        if record is None:
            return

        node_name = _require_non_empty_str(node_name, "node_name")

        if record.node_name != node_name:
            raise ValueError(
                f"Node mismatch for snapshot visit "
                f"(vehicle_name={vehicle_name!r}, visit_id={visit_id}): "
                f"registered node_name={record.node_name!r}, "
                f"notification node_name={node_name!r}."
            )

        if record.was_arrived_at_snapshot:
            raise ValueError(
                f"Duplicate arrival notification for a snapshot-arrived visit "
                f"(vehicle_name={vehicle_name!r}, visit_id={visit_id})."
            )

        if (
            record.baseline_arrival_timestep is not None
            or record.arrival_tiebreaker is not None
            or record.route_next_link_name is not None
        ):
            raise ValueError(
                f"Duplicate or partial arrival state for snapshot visit "
                f"(vehicle_name={vehicle_name!r}, visit_id={visit_id})."
            )

        baseline_arrival_timestep = _require_timestep(
            baseline_arrival_timestep, "baseline_arrival_timestep"
        )
        arrival_tiebreaker = _require_arrival_tiebreaker(
            arrival_tiebreaker, "arrival_tiebreaker"
        )
        route_next_link_name = _require_route_next_link_name(
            route_next_link_name, "route_next_link_name"
        )

        record.baseline_arrival_timestep = baseline_arrival_timestep
        record.arrival_tiebreaker = arrival_tiebreaker
        record.route_next_link_name = route_next_link_name

    def prepare_baseline_passage_recording(
        self,
        *,
        vehicle_name: str,
        visit_id: int,
        node_name: str,
    ) -> OrderControlBaselineVisitRecord | None:
        """
        Validate a fixed visit before UXsim performs the physical node passage.

        Returns None when the vehicle is outside the snapshot-fixed set.
        """
        vehicle_name = _require_non_empty_str(vehicle_name, "vehicle_name")

        record_for_vehicle = self._visit_record_by_vehicle_name.get(vehicle_name)
        if record_for_vehicle is None:
            return None

        visit_id = _require_positive_int(visit_id, "visit_id")

        primary_key = (vehicle_name, visit_id)
        record = self._visit_records_by_primary_key.get(primary_key)
        if record is None:
            raise ValueError(
                f"visit_id mismatch for snapshot-fixed vehicle "
                f"{vehicle_name!r}: registered visit_id="
                f"{record_for_vehicle.visit_id}, requested visit_id={visit_id}."
            )

        node_name = _require_non_empty_str(node_name, "node_name")

        if record.node_name != node_name:
            raise ValueError(
                f"Node mismatch for snapshot visit passage "
                f"(vehicle_name={vehicle_name!r}, visit_id={visit_id}): "
                f"registered node_name={record.node_name!r}, "
                f"passage node_name={node_name!r}."
            )

        if record.baseline_arrival_timestep is None:
            raise ValueError(
                f"Passage attempted before baseline arrival is recorded for "
                f"(vehicle_name={vehicle_name!r}, visit_id={visit_id})."
            )
        if record.arrival_tiebreaker is None:
            raise ValueError(
                f"Passage attempted without arrival_tiebreaker for "
                f"(vehicle_name={vehicle_name!r}, visit_id={visit_id})."
            )
        if record.route_next_link_name is None:
            raise ValueError(
                f"Passage attempted without route_next_link_name for "
                f"(vehicle_name={vehicle_name!r}, visit_id={visit_id})."
            )
        if record.baseline_passage_timestep is not None:
            raise ValueError(
                f"Duplicate passage recording for "
                f"(vehicle_name={vehicle_name!r}, visit_id={visit_id})."
            )

        return record

    def apply_baseline_passage_timestep(
        self,
        record: OrderControlBaselineVisitRecord,
        baseline_passage_timestep: int,
    ) -> None:
        """
        Set baseline_passage_timestep on a visit validated by prepare_baseline_passage_recording.
        """
        baseline_passage_timestep = _require_timestep(
            baseline_passage_timestep, "baseline_passage_timestep"
        )
        record.baseline_passage_timestep = baseline_passage_timestep

    def export_node_baseline_visits(self, node_name: str) -> list[dict]:
        """Return plain dict copies for one node. Order is not rank order."""
        node_name = _require_non_empty_str(node_name, "node_name")
        records = self._visit_records_by_node_name.get(node_name, [])
        return [self._visit_record_to_plain_dict(record) for record in records]

    def get_baseline_visit_snapshot(
        self, vehicle_name: str, visit_id: int
    ) -> dict | None:
        """Return a plain dict copy for one fixed visit, or None if not registered."""
        vehicle_name = _require_non_empty_str(vehicle_name, "vehicle_name")
        visit_id = _require_positive_int(visit_id, "visit_id")
        record = self._visit_records_by_primary_key.get((vehicle_name, visit_id))
        if record is None:
            return None
        return self._visit_record_to_plain_dict(record)

    def _visit_record_to_plain_dict(
        self, record: OrderControlBaselineVisitRecord
    ) -> dict:
        return {
            "vehicle_name": record.vehicle_name,
            "vehicle_id": record.vehicle_id,
            "node_name": record.node_name,
            "inlink_name": record.inlink_name,
            "visit_id": record.visit_id,
            "was_arrived_at_snapshot": record.was_arrived_at_snapshot,
            "baseline_arrival_timestep": record.baseline_arrival_timestep,
            "arrival_tiebreaker": record.arrival_tiebreaker,
            "route_next_link_name": record.route_next_link_name,
            "baseline_passage_timestep": record.baseline_passage_timestep,
        }
