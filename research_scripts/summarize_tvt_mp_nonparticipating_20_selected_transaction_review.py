"""
Build a human-review CSV from selected-transaction fundamentals outputs.

Reads only the existing summary and parties CSV files. No simulation,
no production imports, and no modification of inputs.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = (
    REPO_ROOT
    / "research_outputs"
    / "trial"
    / (
        "tvt_mp_two_cross_intersections_downstream_spillback_"
        "extended_south_pulse_seed_1_nonparticipation_seed_3_"
        "selected_transaction_fundamentals_diagnostic"
    )
)
SUMMARY_CSV_NAME = "selected_transaction_fundamentals_summary.csv"
PARTIES_CSV_NAME = "selected_transaction_fundamentals_parties.csv"
REVIEW_CSV_NAME = "selected_transaction_fundamentals_review.csv"

PAYMENT_BALANCE_REL_TOL = 1e-12
PAYMENT_BALANCE_ABS_TOL = 1e-12

EXPECTED_TRANSACTION_COUNT = 63
EXPECTED_PARTY_ROW_COUNT = 233

REVIEW_COLUMNS = (
    "decision_label",
    "scenario_name",
    "tvt_decision_timestep",
    "node_name",
    "candidate_identity",
    "buyers_sorted",
    "sellers_sorted",
    "nonparticipating_visits_sorted",
    "selection_reasons",
    "buyer_count",
    "seller_count",
    "nonparticipating_count",
    "trade_scope_count",
    "baseline_order_visit_keys",
    "candidate_order_visit_keys",
    "baseline_local_rank",
    "post_trade_local_rank",
    "vehicle_name",
    "visit_id",
    "visit_key",
    "role",
    "participates_in_order_exchange",
    "is_right_of_entry_holder",
    "inlink_name",
    "formal_route_next_link_name",
    "predicted_route_next_link_name",
    "actual_route_next_link_name",
    "baseline_arrival_timestep",
    "actual_arrival_timestep",
    "baseline_minus_actual_arrival_timesteps",
    "baseline_passage_timestep",
    "candidate_passage_timestep",
    "actual_passage_timestep",
    "baseline_minus_candidate_passage_timesteps",
    "baseline_minus_actual_passage_timesteps",
    "candidate_minus_actual_passage_timesteps",
    "predicted_observation_status",
    "actual_observation_status",
    "baseline_minus_candidate_local_rank",
    "assigned_rank",
    "actual_node_passage_rank",
    "assigned_minus_actual_node_rank",
    "actual_rank_change",
    "binding_sequence_auxiliary_rank",
    "true_vot_per_second",
    "declared_vot_per_second",
    "economically_feasible",
    "candidate_infeasibility_reasons",
    "individual_economic_condition_status",
    "individual_economic_condition_reason",
    "expected_time_saving_timesteps",
    "expected_delay_timesteps",
    "gross_time_value_G_b",
    "required_compensation_R_s",
    "satisfaction_status",
    "satisfaction_reason",
    "trade_ex_post_evaluation_status",
    "actual_evaluation_available",
    "official_payment",
    "official_compensation",
    "effective_payment_amount",
    "effective_compensation_amount",
    "monetary_transfer_participation_status",
    "payment_record_status",
    "compensation_record_status",
    "reference_payment",
    "reference_compensation",
    "reference_payment_status",
    "reference_compensation_status",
    "realized_time_value",
    "realized_delay_loss",
    "realized_gain",
    "predicted_signed_time_difference_timesteps",
    "actual_signed_time_difference_timesteps",
    "predicted_external_effect_value",
    "actual_external_effect_value",
    "total_G",
    "total_R",
    "surplus",
    "total_official_payment",
    "total_official_compensation",
    "payment_balance_difference",
    "payment_balance_satisfied",
    "transaction_actual_evaluation_available",
    "transaction_trade_ex_post_evaluation_status",
    "arrival_difference_check",
    "baseline_candidate_passage_difference_check",
    "baseline_actual_passage_difference_check",
    "candidate_actual_passage_difference_check",
    "baseline_candidate_local_rank_check",
    "assigned_actual_rank_difference_check",
    "actual_rank_change_check",
    "nonparticipating_rank_protection_check",
    "role_monetary_contract_check",
    "payment_balance_check",
    "transaction_row_count_check",
    "transaction_role_count_check",
    "baseline_rank_sequence_check",
    "candidate_rank_sequence_check",
    "limited_check_status",
    "limited_check_notes",
)

CHECK_PASS = "pass"
CHECK_FAIL = "fail"
CHECK_NOT_OBSERVABLE = "not_observable"
CHECK_NOT_APPLICABLE = "not_applicable"
CHECK_NOT_CHECKED = "not_checked"


def _blank(value) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text == ""


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "True" if value is True else "False"
    return str(value)


def _parse_int(value):
    if _blank(value):
        return None
    text = str(value).strip()
    try:
        parsed = int(text)
    except ValueError:
        return None
    if type(parsed) is not int:
        return None
    return parsed


def _parse_float(value):
    if _blank(value):
        return None
    text = str(value).strip()
    try:
        parsed = float(text)
    except ValueError:
        return None
    if type(parsed) is bool or not math.isfinite(parsed):
        return None
    return parsed


def _parse_bool(value):
    if _blank(value):
        return None
    text = str(value).strip()
    if text == "True":
        return True
    if text == "False":
        return False
    return None


def _subtract_ints(left, right):
    if type(left) is not int or type(right) is not int:
        return None
    return left - right


def _int_equal(stored, computed) -> str:
    if computed is None:
        return CHECK_NOT_OBSERVABLE
    stored_int = _parse_int(stored)
    if stored_int is None:
        return CHECK_FAIL
    if stored_int == computed:
        return CHECK_PASS
    return CHECK_FAIL


def _transaction_key(row: dict) -> tuple:
    timestep = _parse_int(row["tvt_decision_timestep"])
    if timestep is None:
        raise RuntimeError("Party row has invalid tvt_decision_timestep.")
    node_name = row["node_name"]
    candidate_identity = row["candidate_identity"]
    return (timestep, node_name, candidate_identity)


def _decision_label(timestep: int, node_name: str, candidate_identity: str) -> str:
    return f"T={timestep} | Node={node_name} | Candidate={candidate_identity}"


def _split_visit_keys(text: str) -> tuple[str, ...]:
    if _blank(text):
        return ()
    parts = []
    for piece in str(text).split("|"):
        piece = piece.strip()
        if piece != "":
            parts.append(piece)
    return tuple(parts)


def _visit_keys_by_rank(rows: list[dict], rank_field: str) -> tuple[str, ...]:
    ranked = []
    for row in rows:
        rank = _parse_int(row[rank_field])
        visit_key = row["visit_key"]
        if rank is None or _blank(visit_key):
            raise RuntimeError("Rank or visit_key is missing inside one transaction.")
        ranked.append((rank, visit_key))
    ranked.sort(key=lambda item: item[0])
    return tuple(visit_key for _rank, visit_key in ranked)


def _trade_scope_visit_keys(rows: list[dict]) -> set[str]:
    keys = set()
    for row in rows:
        if _blank(row["visit_key"]):
            raise RuntimeError("Trade-scope row is missing visit_key.")
        keys.add(row["visit_key"])
    return keys


def _filter_order_to_trade_scope(order_text: str, trade_scope_keys: set[str]) -> tuple[str, ...]:
    filtered = []
    for visit_key in _split_visit_keys(order_text):
        if visit_key in trade_scope_keys:
            filtered.append(visit_key)
    return tuple(filtered)


def _duplicate_ranks(rows: list[dict], rank_field: str) -> bool:
    seen = set()
    for row in rows:
        rank = _parse_int(row[rank_field])
        if rank is None:
            return True
        if rank in seen:
            return True
        seen.add(rank)
    return False


def _payment_balance_satisfied(total_payment, total_compensation) -> bool:
    if type(total_payment) is bool or type(total_payment) not in (int, float):
        return False
    if type(total_compensation) is bool or type(total_compensation) not in (int, float):
        return False
    if not math.isfinite(total_payment) or not math.isfinite(total_compensation):
        return False
    return math.isclose(
        total_payment,
        total_compensation,
        rel_tol=PAYMENT_BALANCE_REL_TOL,
        abs_tol=PAYMENT_BALANCE_ABS_TOL,
    )


def _check_role_monetary(row: dict) -> str:
    role = row["role"]
    participates = _parse_bool(row["participates_in_order_exchange"])
    official_payment = row["official_payment"]
    official_compensation = row["official_compensation"]
    declared_vot = row["declared_vot_per_second"]
    effective_payment = _parse_float(row["effective_payment_amount"])
    effective_compensation = _parse_float(row["effective_compensation_amount"])
    payment_status = row["payment_record_status"]
    compensation_status = row["compensation_record_status"]
    monetary_status = row["monetary_transfer_participation_status"]

    if role == "buyer":
        payment_value = _parse_float(official_payment)
        if participates is not True:
            return CHECK_FAIL
        if payment_value is None:
            return CHECK_FAIL
        if effective_payment is None or effective_payment != payment_value:
            return CHECK_FAIL
        if effective_compensation is None or effective_compensation != 0:
            return CHECK_FAIL
        if payment_status != "present":
            return CHECK_FAIL
        if compensation_status != "absent_not_applicable":
            return CHECK_FAIL
        return CHECK_PASS
    if role == "seller":
        compensation_value = _parse_float(official_compensation)
        if participates is not True:
            return CHECK_FAIL
        if compensation_value is None:
            return CHECK_FAIL
        if effective_compensation is None or effective_compensation != compensation_value:
            return CHECK_FAIL
        if effective_payment is None or effective_payment != 0:
            return CHECK_FAIL
        if compensation_status != "present":
            return CHECK_FAIL
        if payment_status != "absent_not_applicable":
            return CHECK_FAIL
        return CHECK_PASS
    if role == "nonparticipating":
        if participates is not False:
            return CHECK_FAIL
        if not _blank(declared_vot):
            return CHECK_FAIL
        if not _blank(official_payment) or not _blank(official_compensation):
            return CHECK_FAIL
        if effective_payment is None or effective_payment != 0:
            return CHECK_FAIL
        if effective_compensation is None or effective_compensation != 0:
            return CHECK_FAIL
        if payment_status != "absent_not_applicable":
            return CHECK_FAIL
        if compensation_status != "absent_not_applicable":
            return CHECK_FAIL
        if monetary_status != "excluded_nonparticipating":
            return CHECK_FAIL
        return CHECK_PASS
    return CHECK_NOT_APPLICABLE


def _check_nonparticipating_rank(row: dict) -> str:
    if row["role"] != "nonparticipating":
        return CHECK_NOT_APPLICABLE
    baseline = _parse_int(row["baseline_local_rank"])
    post_trade = _parse_int(row["post_trade_local_rank"])
    if baseline is None or post_trade is None:
        return CHECK_FAIL
    if baseline == post_trade:
        return CHECK_PASS
    return CHECK_FAIL


def _transaction_checks(party_rows: list[dict], summary: dict) -> dict:
    trade_scope_count = _parse_int(summary["trade_scope_count"])
    buyer_count = _parse_int(summary["buyer_count"])
    seller_count = _parse_int(summary["seller_count"])
    nonparticipating_count = _parse_int(summary["nonparticipating_count"])
    if (
        trade_scope_count is None
        or buyer_count is None
        or seller_count is None
        or nonparticipating_count is None
    ):
        raise RuntimeError("Summary row has invalid role counts.")
    role_counts = {"buyer": 0, "seller": 0, "nonparticipating": 0}
    for row in party_rows:
        role = row["role"]
        if role in role_counts:
            role_counts[role] = role_counts[role] + 1
    row_count_check = CHECK_PASS
    if len(party_rows) != trade_scope_count:
        row_count_check = CHECK_FAIL
    role_count_check = CHECK_PASS
    if (
        role_counts["buyer"] != buyer_count
        or role_counts["seller"] != seller_count
        or role_counts["nonparticipating"] != nonparticipating_count
    ):
        role_count_check = CHECK_FAIL
    baseline_sequence_check = CHECK_PASS
    candidate_sequence_check = CHECK_PASS
    if _duplicate_ranks(party_rows, "baseline_local_rank"):
        baseline_sequence_check = CHECK_FAIL
    if _duplicate_ranks(party_rows, "post_trade_local_rank"):
        candidate_sequence_check = CHECK_FAIL
    trade_scope_keys = _trade_scope_visit_keys(party_rows)
    baseline_keys = _visit_keys_by_rank(party_rows, "baseline_local_rank")
    candidate_keys = _visit_keys_by_rank(party_rows, "post_trade_local_rank")
    baseline_order_scope = _filter_order_to_trade_scope(
        summary["baseline_order_visit_keys"],
        trade_scope_keys,
    )
    candidate_order_scope = _filter_order_to_trade_scope(
        summary["candidate_order_visit_keys"],
        trade_scope_keys,
    )
    if baseline_keys != baseline_order_scope:
        baseline_sequence_check = CHECK_FAIL
    if candidate_keys != candidate_order_scope:
        candidate_sequence_check = CHECK_FAIL
    total_payment = _parse_float(summary["total_official_payment"])
    total_compensation = _parse_float(summary["total_official_compensation"])
    stored_difference = _parse_float(summary["payment_balance_difference"])
    stored_satisfied = _parse_bool(summary["payment_balance_satisfied"])
    payment_balance_check = CHECK_FAIL
    if total_payment is not None and total_compensation is not None:
        raw_difference = total_payment - total_compensation
        expected_satisfied = _payment_balance_satisfied(total_payment, total_compensation)
        difference_ok = stored_difference is not None and math.isclose(
            stored_difference,
            raw_difference,
            rel_tol=0.0,
            abs_tol=0.0,
        )
        satisfied_ok = stored_satisfied is not None and stored_satisfied == expected_satisfied
        if difference_ok and satisfied_ok:
            payment_balance_check = CHECK_PASS
    return {
        "transaction_row_count_check": row_count_check,
        "transaction_role_count_check": role_count_check,
        "baseline_rank_sequence_check": baseline_sequence_check,
        "candidate_rank_sequence_check": candidate_sequence_check,
        "payment_balance_check": payment_balance_check,
    }


def _row_checks(row: dict, transaction_checks: dict) -> dict:
    baseline_arrival = _parse_int(row["baseline_arrival_timestep"])
    actual_arrival = _parse_int(row["actual_arrival_timestep"])
    if baseline_arrival is not None and actual_arrival is not None:
        arrival_difference_check = _int_equal(
            row["baseline_minus_actual_arrival_timesteps"],
            _subtract_ints(baseline_arrival, actual_arrival),
        )
    elif _blank(row["actual_arrival_timestep"]):
        arrival_difference_check = CHECK_NOT_OBSERVABLE
    else:
        arrival_difference_check = CHECK_NOT_OBSERVABLE

    baseline_passage = _parse_int(row["baseline_passage_timestep"])
    candidate_passage = _parse_int(row["candidate_passage_timestep"])
    actual_passage = _parse_int(row["actual_passage_timestep"])

    if baseline_passage is not None and candidate_passage is not None:
        baseline_candidate_passage_difference_check = _int_equal(
            row["baseline_minus_candidate_passage_timesteps"],
            _subtract_ints(baseline_passage, candidate_passage),
        )
    else:
        baseline_candidate_passage_difference_check = CHECK_NOT_OBSERVABLE

    if baseline_passage is not None and actual_passage is not None:
        baseline_actual_passage_difference_check = _int_equal(
            row["baseline_minus_actual_passage_timesteps"],
            _subtract_ints(baseline_passage, actual_passage),
        )
    elif _blank(row["actual_passage_timestep"]):
        baseline_actual_passage_difference_check = CHECK_NOT_OBSERVABLE
    else:
        baseline_actual_passage_difference_check = CHECK_NOT_OBSERVABLE

    if candidate_passage is not None and actual_passage is not None:
        candidate_actual_passage_difference_check = _int_equal(
            row["candidate_minus_actual_passage_timesteps"],
            _subtract_ints(candidate_passage, actual_passage),
        )
    elif _blank(row["actual_passage_timestep"]):
        candidate_actual_passage_difference_check = CHECK_NOT_OBSERVABLE
    else:
        candidate_actual_passage_difference_check = CHECK_NOT_OBSERVABLE

    baseline_rank = _parse_int(row["baseline_local_rank"])
    post_trade_rank = _parse_int(row["post_trade_local_rank"])
    if baseline_rank is not None and post_trade_rank is not None:
        baseline_candidate_local_rank_check = _int_equal(
            row["baseline_minus_candidate_local_rank"],
            _subtract_ints(baseline_rank, post_trade_rank),
        )
    else:
        baseline_candidate_local_rank_check = CHECK_NOT_OBSERVABLE

    assigned_rank = _parse_int(row["assigned_rank"])
    actual_rank = _parse_int(row["actual_node_passage_rank"])
    if assigned_rank is not None and actual_rank is not None:
        assigned_actual_rank_difference_check = _int_equal(
            row["assigned_minus_actual_node_rank"],
            _subtract_ints(assigned_rank, actual_rank),
        )
        actual_rank_change_check = _int_equal(
            row["actual_rank_change"],
            _subtract_ints(assigned_rank, actual_rank),
        )
    elif _blank(row["actual_node_passage_rank"]):
        assigned_actual_rank_difference_check = CHECK_NOT_OBSERVABLE
        actual_rank_change_check = CHECK_NOT_OBSERVABLE
    else:
        assigned_actual_rank_difference_check = CHECK_NOT_OBSERVABLE
        actual_rank_change_check = CHECK_NOT_OBSERVABLE

    checks = {
        "arrival_difference_check": arrival_difference_check,
        "baseline_candidate_passage_difference_check": baseline_candidate_passage_difference_check,
        "baseline_actual_passage_difference_check": baseline_actual_passage_difference_check,
        "candidate_actual_passage_difference_check": candidate_actual_passage_difference_check,
        "baseline_candidate_local_rank_check": baseline_candidate_local_rank_check,
        "assigned_actual_rank_difference_check": assigned_actual_rank_difference_check,
        "actual_rank_change_check": actual_rank_change_check,
        "nonparticipating_rank_protection_check": _check_nonparticipating_rank(row),
        "role_monetary_contract_check": _check_role_monetary(row),
        "payment_balance_check": transaction_checks["payment_balance_check"],
        "transaction_row_count_check": transaction_checks["transaction_row_count_check"],
        "transaction_role_count_check": transaction_checks["transaction_role_count_check"],
        "baseline_rank_sequence_check": transaction_checks["baseline_rank_sequence_check"],
        "candidate_rank_sequence_check": transaction_checks["candidate_rank_sequence_check"],
    }
    return checks


def _limited_status(checks: dict) -> tuple[str, str]:
    failed = []
    passed = False
    for name, value in checks.items():
        if value == CHECK_FAIL:
            failed.append(name)
        elif value == CHECK_PASS:
            passed = True
    if len(failed) > 0:
        return CHECK_FAIL, "|".join(failed)
    if passed is True:
        return CHECK_PASS, ""
    return CHECK_NOT_CHECKED, ""


def _load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _sort_key(row: dict) -> tuple:
    timestep = _parse_int(row["tvt_decision_timestep"])
    if timestep is None:
        raise RuntimeError("Cannot sort rows without tvt_decision_timestep.")
    baseline_rank = _parse_int(row["baseline_local_rank"])
    if baseline_rank is None:
        raise RuntimeError("Cannot sort rows without baseline_local_rank.")
    return (
        timestep,
        row["node_name"],
        row["candidate_identity"],
        baseline_rank,
        row["visit_key"],
    )


def _build_review_rows() -> tuple[list[dict], list[dict]]:
    summary_path = INPUT_DIR / SUMMARY_CSV_NAME
    parties_path = INPUT_DIR / PARTIES_CSV_NAME
    if not summary_path.is_file():
        raise RuntimeError(f"Missing summary CSV: {summary_path}.")
    if not parties_path.is_file():
        raise RuntimeError(f"Missing parties CSV: {parties_path}.")
    summaries = _load_csv(summary_path)
    parties = _load_csv(parties_path)
    summary_by_key = {}
    for summary in summaries:
        key = (
            _parse_int(summary["tvt_decision_timestep"]),
            summary["node_name"],
            summary["candidate_identity"],
        )
        if key[0] is None:
            raise RuntimeError("Summary row has invalid tvt_decision_timestep.")
        if key in summary_by_key:
            raise RuntimeError(f"Duplicate summary transaction {key!r}.")
        summary_by_key[key] = summary
    parties_by_transaction: dict[tuple, list[dict]] = {}
    for party in parties:
        key = _transaction_key(party)
        if key not in summary_by_key:
            raise RuntimeError(f"Party row has no summary for {key!r}.")
        parties_by_transaction.setdefault(key, []).append(party)
    if len(summary_by_key) != EXPECTED_TRANSACTION_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_TRANSACTION_COUNT} transactions, got {len(summary_by_key)}."
        )
    sorted_parties = sorted(parties, key=_sort_key)
    if len(sorted_parties) != EXPECTED_PARTY_ROW_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_PARTY_ROW_COUNT} party rows, got {len(sorted_parties)}."
        )
    transaction_checks_by_key = {}
    for key, party_rows in parties_by_transaction.items():
        transaction_checks_by_key[key] = _transaction_checks(
            sorted(party_rows, key=_sort_key),
            summary_by_key[key],
        )
    review_rows = []
    failures = []
    for party in sorted_parties:
        key = _transaction_key(party)
        summary = summary_by_key[key]
        timestep = key[0]
        checks = _row_checks(party, transaction_checks_by_key[key])
        limited_status, limited_notes = _limited_status(checks)
        review_row = {
            "decision_label": _decision_label(timestep, key[1], key[2]),
            "scenario_name": party["scenario_name"],
            "tvt_decision_timestep": party["tvt_decision_timestep"],
            "node_name": party["node_name"],
            "candidate_identity": party["candidate_identity"],
            "buyers_sorted": party["buyers_sorted"],
            "sellers_sorted": party["sellers_sorted"],
            "nonparticipating_visits_sorted": party["nonparticipating_visits_sorted"],
            "selection_reasons": party["selection_reasons"],
            "buyer_count": summary["buyer_count"],
            "seller_count": summary["seller_count"],
            "nonparticipating_count": summary["nonparticipating_count"],
            "trade_scope_count": summary["trade_scope_count"],
            "baseline_order_visit_keys": party["baseline_order_visit_keys"],
            "candidate_order_visit_keys": party["candidate_order_visit_keys"],
            "baseline_local_rank": party["baseline_local_rank"],
            "post_trade_local_rank": party["post_trade_local_rank"],
            "vehicle_name": party["vehicle_name"],
            "visit_id": party["visit_id"],
            "visit_key": party["visit_key"],
            "role": party["role"],
            "participates_in_order_exchange": party["participates_in_order_exchange"],
            "is_right_of_entry_holder": party["is_right_of_entry_holder"],
            "inlink_name": party["inlink_name"],
            "formal_route_next_link_name": party["formal_route_next_link_name"],
            "predicted_route_next_link_name": party["predicted_route_next_link_name"],
            "actual_route_next_link_name": party["actual_route_next_link_name"],
            "baseline_arrival_timestep": party["baseline_arrival_timestep"],
            "actual_arrival_timestep": party["actual_arrival_timestep"],
            "baseline_minus_actual_arrival_timesteps": party[
                "baseline_minus_actual_arrival_timesteps"
            ],
            "baseline_passage_timestep": party["baseline_passage_timestep"],
            "candidate_passage_timestep": party["candidate_passage_timestep"],
            "actual_passage_timestep": party["actual_passage_timestep"],
            "baseline_minus_candidate_passage_timesteps": party[
                "baseline_minus_candidate_passage_timesteps"
            ],
            "baseline_minus_actual_passage_timesteps": party[
                "baseline_minus_actual_passage_timesteps"
            ],
            "candidate_minus_actual_passage_timesteps": party[
                "candidate_minus_actual_passage_timesteps"
            ],
            "predicted_observation_status": party["predicted_observation_status"],
            "actual_observation_status": party["actual_observation_status"],
            "baseline_minus_candidate_local_rank": party["baseline_minus_candidate_local_rank"],
            "assigned_rank": party["assigned_rank"],
            "actual_node_passage_rank": party["actual_node_passage_rank"],
            "assigned_minus_actual_node_rank": party["assigned_minus_actual_node_rank"],
            "actual_rank_change": party["actual_rank_change"],
            "binding_sequence_auxiliary_rank": party["binding_sequence_auxiliary_rank"],
            "true_vot_per_second": party["true_vot_per_second"],
            "declared_vot_per_second": party["declared_vot_per_second"],
            "economically_feasible": party["economically_feasible"],
            "candidate_infeasibility_reasons": party["candidate_infeasibility_reasons"],
            "individual_economic_condition_status": party["individual_economic_condition_status"],
            "individual_economic_condition_reason": party["individual_economic_condition_reason"],
            "expected_time_saving_timesteps": party["expected_time_saving_timesteps"],
            "expected_delay_timesteps": party["expected_delay_timesteps"],
            "gross_time_value_G_b": party["gross_time_value_G_b"],
            "required_compensation_R_s": party["required_compensation_R_s"],
            "satisfaction_status": party["satisfaction_status"],
            "satisfaction_reason": party["satisfaction_reason"],
            "trade_ex_post_evaluation_status": party["trade_ex_post_evaluation_status"],
            "actual_evaluation_available": party["actual_evaluation_available"],
            "official_payment": party["official_payment"],
            "official_compensation": party["official_compensation"],
            "effective_payment_amount": party["effective_payment_amount"],
            "effective_compensation_amount": party["effective_compensation_amount"],
            "monetary_transfer_participation_status": party[
                "monetary_transfer_participation_status"
            ],
            "payment_record_status": party["payment_record_status"],
            "compensation_record_status": party["compensation_record_status"],
            "reference_payment": party["reference_payment"],
            "reference_compensation": party["reference_compensation"],
            "reference_payment_status": party["reference_payment_status"],
            "reference_compensation_status": party["reference_compensation_status"],
            "realized_time_value": party["realized_time_value"],
            "realized_delay_loss": party["realized_delay_loss"],
            "realized_gain": party["realized_gain"],
            "predicted_signed_time_difference_timesteps": party[
                "predicted_signed_time_difference_timesteps"
            ],
            "actual_signed_time_difference_timesteps": party[
                "actual_signed_time_difference_timesteps"
            ],
            "predicted_external_effect_value": party["predicted_external_effect_value"],
            "actual_external_effect_value": party["actual_external_effect_value"],
            "total_G": summary["total_G"],
            "total_R": summary["total_R"],
            "surplus": summary["surplus"],
            "total_official_payment": summary["total_official_payment"],
            "total_official_compensation": summary["total_official_compensation"],
            "payment_balance_difference": summary["payment_balance_difference"],
            "payment_balance_satisfied": summary["payment_balance_satisfied"],
            "transaction_actual_evaluation_available": summary["actual_evaluation_available"],
            "transaction_trade_ex_post_evaluation_status": summary[
                "trade_ex_post_evaluation_status"
            ],
            "limited_check_status": limited_status,
            "limited_check_notes": limited_notes,
        }
        review_row.update(checks)
        review_rows.append(review_row)
        if limited_status == CHECK_FAIL:
            for check_name, check_value in checks.items():
                if check_value != CHECK_FAIL:
                    continue
                failures.append(
                    {
                        "tvt_decision_timestep": timestep,
                        "node_name": key[1],
                        "candidate_identity": key[2],
                        "visit_key": party["visit_key"],
                        "check_name": check_name,
                    }
                )
    return review_rows, failures


def _write_review_csv(rows: list[dict]) -> Path:
    output_path = INPUT_DIR / REVIEW_CSV_NAME
    if output_path.exists():
        raise RuntimeError(f"Review CSV already exists: {output_path}.")
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row[column]) for column in REVIEW_COLUMNS})
    return output_path


def main() -> int:
    review_rows, failures = _build_review_rows()
    output_path = _write_review_csv(review_rows)
    timesteps = [_parse_int(row["tvt_decision_timestep"]) for row in review_rows]
    timesteps = [value for value in timesteps if value is not None]
    limited_pass = sum(1 for row in review_rows if row["limited_check_status"] == CHECK_PASS)
    limited_fail = sum(1 for row in review_rows if row["limited_check_status"] == CHECK_FAIL)
    nonparticipating_rows = sum(1 for row in review_rows if row["role"] == "nonparticipating")
    np_rank_pass = sum(
        1
        for row in review_rows
        if row["nonparticipating_rank_protection_check"] == CHECK_PASS
    )
    np_rank_fail = sum(
        1
        for row in review_rows
        if row["nonparticipating_rank_protection_check"] == CHECK_FAIL
    )
    transaction_row_count_failures = sum(
        1 for row in review_rows if row["transaction_row_count_check"] == CHECK_FAIL
    )
    transaction_role_count_failures = sum(
        1 for row in review_rows if row["transaction_role_count_check"] == CHECK_FAIL
    )
    baseline_rank_sequence_failures = sum(
        1 for row in review_rows if row["baseline_rank_sequence_check"] == CHECK_FAIL
    )
    candidate_rank_sequence_failures = sum(
        1 for row in review_rows if row["candidate_rank_sequence_check"] == CHECK_FAIL
    )
    role_monetary_contract_failures = sum(
        1 for row in review_rows if row["role_monetary_contract_check"] == CHECK_FAIL
    )
    payment_balance_failures = sum(
        1 for row in review_rows if row["payment_balance_check"] == CHECK_FAIL
    )
    print(f"transaction_count: {len(set(_transaction_key(row) for row in review_rows))}")
    print(f"party_row_count: {len(review_rows)}")
    print(f"first_decision_T: {min(timesteps)}")
    print(f"last_decision_T: {max(timesteps)}")
    print(f"limited_check_pass_rows: {limited_pass}")
    print(f"limited_check_fail_rows: {limited_fail}")
    print(f"nonparticipating_rows: {nonparticipating_rows}")
    print(f"nonparticipating_rank_protection_pass: {np_rank_pass}")
    print(f"nonparticipating_rank_protection_fail: {np_rank_fail}")
    print(f"transaction_row_count_failures: {transaction_row_count_failures}")
    print(f"transaction_role_count_failures: {transaction_role_count_failures}")
    print(f"baseline_rank_sequence_failures: {baseline_rank_sequence_failures}")
    print(f"candidate_rank_sequence_failures: {candidate_rank_sequence_failures}")
    print(f"role_monetary_contract_failures: {role_monetary_contract_failures}")
    print(f"payment_balance_failures: {payment_balance_failures}")
    print(f"output_csv: {output_path}")
    if len(failures) > 0:
        seen = set()
        for failure in failures:
            marker = (
                failure["tvt_decision_timestep"],
                failure["node_name"],
                failure["candidate_identity"],
                failure["visit_key"],
                failure["check_name"],
            )
            if marker in seen:
                continue
            seen.add(marker)
            print(
                "failure: "
                f"T={failure['tvt_decision_timestep']} "
                f"Node={failure['node_name']} "
                f"Candidate={failure['candidate_identity']} "
                f"VisitKey={failure['visit_key']} "
                f"check={failure['check_name']}"
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
