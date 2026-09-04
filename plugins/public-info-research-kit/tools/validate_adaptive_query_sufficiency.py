#!/usr/bin/env python3
"""Validate D-237 applicability, sufficiency, incremental batches and query promotion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from retrieval_task_policy import validate_task_authorization


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "schemas/adaptive_query_sufficiency_contract.v1.json"
CONTRACT = json.loads(DEFAULT_CONTRACT.read_text(encoding="utf-8"))
APPLICABILITY = CONTRACT["applicability"]
ACCEPTANCE_MODES = set(CONTRACT["acceptance_modes"])
BATCH_STATES = set(CONTRACT["batch_states"])
SUFFICIENCY_STATUSES = set(CONTRACT["evidence_sufficiency_statuses"])
MARGINAL_GAIN = set(CONTRACT["marginal_information_gain_assessments"])
FAILURE_CLASSES = {None, *CONTRACT["failure_classes"]}
RECOMMENDATION_STATUSES = set(CONTRACT["query_recommendation"]["statuses"])
HUMAN_REVIEW_STATUSES = set(CONTRACT["query_recommendation"]["human_review_statuses"])
ATTRIBUTION_STATUSES = set(CONTRACT["query_attribution_statuses"])
SUFFICIENCY_POLICIES = set(APPLICABILITY["allowed_policies"])
SIMPLE_RETRIEVAL_TYPES = set(APPLICABILITY["simple_direct_retrieval_types"])
EXEMPTION_FORBIDDEN_CHARACTERISTICS = set(APPLICABILITY["research_characteristics_forbid_exemption"])
MINIMUM_RECOMMENDED_TASKS = CONTRACT["query_recommendation"]["minimum_validated_task_count_for_recommended"]
PROMOTION_REVIEW_SCHEMA = CONTRACT["query_recommendation"]["review_batch_schema"]
EXPLAINABLE_FLOOR_SHORTFALLS = {
    "identity_collision",
    "content_supply_gap",
    "query_transport_failure",
    "route_control_failure",
    "source_render_failure",
    "safety_stop",
    "evidence_conversion_failure",
}


def result(status: str, passed: bool, **extra: object) -> dict[str, Any]:
    return {
        "schema": "adaptive_query_sufficiency_validation.v1",
        "status": status,
        "passed": passed,
        "platform_opened": False,
        "external_write_executed": False,
        **extra,
    }


def applicability_result(status: str, passed: bool, **extra: object) -> dict[str, Any]:
    return {
        "schema": "query_sufficiency_applicability_validation.v1",
        "status": status,
        "passed": passed,
        "platform_opened": False,
        "external_write_executed": False,
        **extra,
    }


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def nonempty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(nonempty(item) for item in value)


def nonnegative_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def validate_applicability(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema") != APPLICABILITY["schema"]:
        return applicability_result("invalid_schema", False)
    task_id = payload.get("task_id")
    if not nonempty(task_id):
        return applicability_result("task_id_required", False)
    route_receipt = payload.get("route_receipt")
    if not isinstance(route_receipt, dict):
        return applicability_result("route_receipt_required", False, task_id=task_id)
    primary_route_id = route_receipt.get("primary_route_id")
    required_gate_ids = route_receipt.get("required_gate_ids")
    if not nonempty(primary_route_id) or not isinstance(required_gate_ids, list) or not all(nonempty(item) for item in required_gate_ids):
        return applicability_result("invalid_route_receipt", False, task_id=task_id)
    if APPLICABILITY["d237_required_gate_id"] not in required_gate_ids:
        return applicability_result(
            "not_applicable_non_retrieval_task",
            True,
            task_id=task_id,
            primary_route_id=primary_route_id,
            d237_required=False,
        )

    policy = payload.get("sufficiency_policy") or APPLICABILITY["default_policy_for_real_retrieval"]
    if policy not in SUFFICIENCY_POLICIES:
        return applicability_result("invalid_sufficiency_policy", False, task_id=task_id)
    characteristics = payload.get("research_characteristics", [])
    if not isinstance(characteristics, list) or not all(nonempty(item) for item in characteristics):
        return applicability_result("invalid_research_characteristics", False, task_id=task_id)
    unknown = sorted(set(characteristics) - EXEMPTION_FORBIDDEN_CHARACTERISTICS)
    if unknown:
        return applicability_result("unknown_research_characteristic", False, task_id=task_id, unknown_characteristics=unknown)

    if policy == "d237_required":
        acceptance_mode = payload.get("acceptance_mode")
        if acceptance_mode not in ACCEPTANCE_MODES:
            return applicability_result(
                "d237_consumer_contract_required",
                False,
                task_id=task_id,
                d237_required=True,
                defaulted_from_omission="sufficiency_policy" not in payload,
                required_field="acceptance_mode",
            )
        return applicability_result(
            "pass",
            True,
            task_id=task_id,
            d237_required=True,
            sufficiency_policy=policy,
            acceptance_mode=acceptance_mode,
            defaulted_from_omission="sufficiency_policy" not in payload,
        )

    exemption = payload.get("simple_direct_retrieval_exemption")
    if not isinstance(exemption, dict):
        return applicability_result("simple_direct_retrieval_exemption_required", False, task_id=task_id, d237_required=True)
    missing = [field for field in APPLICABILITY["required_exemption_fields"] if not nonempty(exemption.get(field))]
    if missing:
        return applicability_result("simple_direct_retrieval_exemption_incomplete", False, task_id=task_id, d237_required=True, missing_fields=missing)
    if exemption.get("exemption_type") not in SIMPLE_RETRIEVAL_TYPES:
        return applicability_result("invalid_simple_direct_retrieval_type", False, task_id=task_id, d237_required=True)
    blocking = sorted(set(characteristics) & EXEMPTION_FORBIDDEN_CHARACTERISTICS)
    if blocking:
        return applicability_result(
            "research_characteristics_forbid_simple_exemption",
            False,
            task_id=task_id,
            d237_required=True,
            blocking_characteristics=blocking,
        )
    return applicability_result(
        "pass",
        True,
        task_id=task_id,
        d237_required=False,
        sufficiency_policy=policy,
        exemption_type=exemption["exemption_type"],
        human_authorization_ref=exemption["human_authorization_ref"],
    )


def validate_review_batches(value: Any) -> tuple[dict[str, dict[str, Any]], dict[str, Any] | None]:
    if value is None:
        return {}, None
    if not isinstance(value, list):
        return {}, result("invalid_promotion_review_batches", False)
    review_map: dict[str, dict[str, Any]] = {}
    covered: set[str] = set()
    for index, batch in enumerate(value):
        if not isinstance(batch, dict) or batch.get("schema") != PROMOTION_REVIEW_SCHEMA:
            return {}, result("invalid_promotion_review_batch", False, review_batch_index=index)
        required = ("review_batch_id", "business_question_family", "covered_query_ids", "status", "reviewer", "reviewed_at")
        missing = [field for field in required if field not in batch]
        if missing:
            return {}, result("invalid_promotion_review_batch", False, review_batch_index=index, missing_fields=missing)
        batch_id = batch.get("review_batch_id")
        family = batch.get("business_question_family")
        query_ids = batch.get("covered_query_ids")
        status = batch.get("status")
        if (
            not nonempty(batch_id)
            or batch_id in review_map
            or not nonempty(family)
            or not nonempty_string_list(query_ids)
            or len(set(query_ids)) != len(query_ids)
            or status not in HUMAN_REVIEW_STATUSES
        ):
            return {}, result("invalid_promotion_review_batch", False, review_batch_index=index)
        duplicate = sorted(set(query_ids) & covered)
        if duplicate:
            return {}, result("promotion_review_query_covered_by_multiple_batches", False, duplicate_query_ids=duplicate)
        if status in {"accepted", "rejected"} and (not nonempty(batch.get("reviewer")) or not nonempty(batch.get("reviewed_at"))):
            return {}, result("promotion_review_batch_human_receipt_missing", False, review_batch_index=index)
        review_map[batch_id] = batch
        covered.update(query_ids)
    return review_map, None


def validate_query(query: Any, index: int) -> dict[str, Any] | None:
    if not isinstance(query, dict):
        return result("invalid_frozen_query", False, query_index=index)
    missing = [field for field in CONTRACT["required_query_fields"] if query.get(field) in (None, "", [])]
    if missing:
        return result("invalid_frozen_query", False, query_index=index, missing_fields=missing)
    if not nonempty_string_list(query.get("atom_signature")) or not nonempty_string_list(query.get("term_provenance")):
        return result("invalid_frozen_query", False, query_index=index)
    for field in ("minimum_result_batches", "minimum_actual_opens"):
        if not positive_integer(query.get(field)):
            return result("invalid_query_execution_floor", False, query_index=index, invalid_field=field)
    return None


def validate_learning_record(
    record: Any,
    index: int,
    qualified_classes: list[str],
    query_by_id: dict[str, dict[str, Any]],
    review_batches: dict[str, dict[str, Any]],
    business_question_family: str,
) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return result("invalid_query_learning_record", False, record_index=index)
    missing = [field for field in CONTRACT["query_learning_required_fields"] if field not in record]
    if missing:
        return result("invalid_query_learning_record", False, record_index=index, missing_fields=missing)
    query_id = record.get("query_id")
    query = query_by_id.get(query_id)
    if query is None or record.get("exact_query_text") != query.get("exact_query_text"):
        return result("query_learning_record_query_mismatch", False, record_index=index)
    if not isinstance(record.get("discovery_evidence_item_ids"), list) or not isinstance(record.get("revisit_evidence_item_ids"), list):
        return result("invalid_query_learning_record", False, record_index=index)
    attribution = record.get("attribution_status")
    if attribution not in ATTRIBUTION_STATUSES:
        return result("invalid_query_learning_record", False, record_index=index)
    counts = record.get("qualification_counts")
    if not isinstance(counts, dict) or not counts:
        return result("invalid_query_learning_record", False, record_index=index)
    if attribution == "recorded":
        missing_classes = [item for item in qualified_classes if item not in counts]
        if missing_classes:
            return result("qualified_class_missing_from_counts", False, record_index=index, missing_qualified_classes=missing_classes)
        if not all(nonnegative_number(value) for value in counts.values()):
            return result("invalid_query_learning_record", False, record_index=index)
        expected_count = sum(counts[item] for item in qualified_classes)
        if record.get("qualified_count") != expected_count:
            return result("qualified_count_mismatch", False, record_index=index, expected_qualified_count=expected_count)
        total = sum(counts.values())
        expected_rate = expected_count / total if total else 0.0
        if not nonnegative_number(record.get("qualified_rate")) or abs(record["qualified_rate"] - expected_rate) > 0.0001:
            return result("qualified_rate_mismatch", False, record_index=index, expected_qualified_rate=round(expected_rate, 4))
    else:
        if any(value is not None for value in counts.values()):
            return result("legacy_attribution_gap_must_not_invent_counts", False, record_index=index)
        if any(record.get(field) is not None for field in ("qualified_count", "qualified_rate", "qualified_project_or_brand_count")):
            return result("legacy_attribution_gap_must_not_invent_counts", False, record_index=index)

    for field in ("result_batch_count", "actual_open_count", "validated_task_count"):
        if not nonnegative_number(record.get(field)):
            return result("invalid_query_learning_record", False, record_index=index, invalid_field=field)
    if attribution == "recorded" and not nonnegative_number(record.get("qualified_project_or_brand_count")):
        return result("invalid_query_learning_record", False, record_index=index)
    if record.get("marginal_information_gain") not in MARGINAL_GAIN:
        return result("invalid_query_learning_record", False, record_index=index, invalid_field="marginal_information_gain")
    if not isinstance(record.get("effective_terms"), list) or not isinstance(record.get("low_efficiency_terms"), list) or not isinstance(record.get("identity_or_object_drift"), list):
        return result("invalid_query_learning_record", False, record_index=index)
    failure_class = record.get("failure_class")
    if failure_class not in FAILURE_CLASSES or not nonempty(record.get("stop_reason")):
        return result("invalid_query_learning_record", False, record_index=index)

    floor_shortfall = (
        record.get("result_batch_count", 0) < query["minimum_result_batches"]
        or record.get("actual_open_count", 0) < query["minimum_actual_opens"]
    )
    if floor_shortfall and failure_class not in EXPLAINABLE_FLOOR_SHORTFALLS:
        return result("query_execution_floor_shortfall_unexplained", False, record_index=index)

    recommendation = record.get("recommended_query_status")
    if recommendation not in RECOMMENDATION_STATUSES:
        return result("invalid_query_learning_record", False, record_index=index)
    human_review = record.get("human_review")
    if not isinstance(human_review, dict) or human_review.get("status") not in HUMAN_REVIEW_STATUSES:
        return result("invalid_query_learning_record", False, record_index=index)
    if recommendation == "recommended":
        if attribution != "recorded":
            return result("recommended_query_attribution_missing", False, record_index=index)
        if record.get("validated_task_count", 0) < MINIMUM_RECOMMENDED_TASKS:
            return result("recommended_query_cross_task_validation_insufficient", False, record_index=index)
        review_batch_id = human_review.get("review_batch_id")
        review = review_batches.get(review_batch_id)
        if human_review.get("status") != "accepted" or review is None:
            return result("recommended_query_not_human_accepted", False, record_index=index)
        if review.get("status") != "accepted" or query_id not in review.get("covered_query_ids", []):
            return result("recommended_query_not_covered_by_accepted_batch", False, record_index=index)
        if review.get("business_question_family") != business_question_family:
            return result("recommended_query_review_family_mismatch", False, record_index=index)
    if recommendation == "rejected" and human_review.get("status") != "rejected":
        return result("rejected_query_requires_human_rejection", False, record_index=index)
    return None


def validate_package(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema") != CONTRACT["package_schema"]:
        return result("invalid_schema", False)
    missing_top = [field for field in CONTRACT["required_package_sections"] if payload.get(field) in (None, "")]
    if missing_top:
        return result("invalid_package", False, missing_fields=missing_top)
    if not nonempty(payload.get("business_question_family")):
        return result("business_question_family_required", False)

    consumer = payload.get("consumer_contract")
    if not isinstance(consumer, dict):
        return result("invalid_consumer_contract", False)
    acceptance_mode = consumer.get("acceptance_mode")
    if acceptance_mode not in ACCEPTANCE_MODES:
        return result("invalid_acceptance_mode", False)
    if acceptance_mode in {"count_based", "hybrid"} and not positive_integer(consumer.get("count_threshold")):
        return result("count_threshold_required", False)
    if acceptance_mode in {"quality_sufficiency", "hybrid"} and not nonempty_string_list(consumer.get("quality_criteria")):
        return result("quality_criteria_required", False)
    qualified_classes = consumer.get("qualified_match_classes")
    if not nonempty_string_list(qualified_classes):
        return result("qualified_match_classes_required", False)
    if not isinstance(consumer.get("non_counted_match_classes"), list):
        return result("invalid_non_counted_match_classes", False)
    diversity = consumer.get("diversity_requirements")
    if not isinstance(diversity, dict):
        return result("diversity_requirements_required", False)
    for field in ("minimum_source_role_count", "minimum_project_or_brand_count", "maximum_qualified_items_per_project_or_brand"):
        if not positive_integer(diversity.get(field)):
            return result("invalid_diversity_requirements", False, invalid_field=field)
    if not nonempty(consumer.get("evidence_usage_permission")):
        return result("evidence_usage_permission_required", False)

    extension = consumer.get("adaptive_extension")
    if not isinstance(extension, dict) or extension.get("authorized") not in {True, False}:
        return result("invalid_adaptive_extension", False)
    if extension.get("authorized") is True:
        if not nonempty(extension.get("authorization_ref")):
            return result("adaptive_extension_authorization_ref_required", False)
        if not positive_integer(extension.get("maximum_incremental_batches")) or not positive_integer(extension.get("time_limit_minutes")) or not nonempty(extension.get("cost_limit")):
            return result("adaptive_extension_limits_required", False)
    else:
        if extension.get("authorization_ref") is not None or extension.get("maximum_incremental_batches") != 0 or extension.get("time_limit_minutes") != 0 or extension.get("cost_limit") is not None:
            return result("unauthorized_adaptive_extension_must_have_zero_limits", False)

    batch = payload.get("batch")
    if not isinstance(batch, dict) or batch.get("batch_state") not in BATCH_STATES:
        return result("invalid_batch_state", False)
    if not nonempty(batch.get("batch_id")) or not nonempty_list(batch.get("queries")):
        return result("invalid_batch", False)
    batch_state = batch["batch_state"]
    if batch_state != "initial_frozen_batch" and not nonempty(batch.get("parent_batch_id")):
        return result("incremental_parent_batch_required", False)
    query_by_id: dict[str, dict[str, Any]] = {}
    for index, query in enumerate(batch["queries"]):
        invalid = validate_query(query, index)
        if invalid:
            return invalid
        query_id = query["query_id"]
        if query_id in query_by_id:
            return result("duplicate_query_id", False, query_id=query_id)
        query_by_id[query_id] = query

    receipt = payload.get("receipt")
    if not isinstance(receipt, dict):
        return result("invalid_receipt", False)
    needs_auth = receipt.get("needs_downstream_authorization")
    if batch_state == "proposed_incremental_batch" and needs_auth is not True:
        return result("incremental_batch_authorization_mismatch", False)
    if batch_state in {"initial_frozen_batch", "approved_incremental_batch", "in_scope_iteration_batch"} and needs_auth is not False:
        return result("incremental_batch_authorization_mismatch", False)
    if batch_state == "in_scope_iteration_batch":
        execution = payload.get("execution_request")
        if not isinstance(execution, dict) or execution.get("task_id") != payload.get("task_id"):
            return result("retrieval_task_scope_mismatch", False)
        valid, status = validate_task_authorization(execution)
        if not valid:
            return result(status, False)
        frozen = {(q.get("query_id"), q.get("exact_query_text")) for q in execution.get("query_plan", []) if isinstance(q, dict) and q.get("execution_state") == "frozen"}
        if any((q.get("query_id"), q.get("exact_query_text")) not in frozen for q in batch["queries"]):
            return result("iteration_queries_not_in_execution_request", False)
    if batch_state == "approved_incremental_batch" and extension.get("authorized") is not True:
        return result("adaptive_extension_not_authorized", False)
    if receipt.get("evidence_sufficiency_status") not in SUFFICIENCY_STATUSES:
        return result("invalid_evidence_sufficiency_status", False)
    if batch_state == "proposed_incremental_batch" and receipt.get("evidence_sufficiency_status") != "not_assessed":
        return result("proposed_incremental_batch_cannot_claim_sufficiency", False)
    marginal = receipt.get("marginal_information_gain")
    required_gain = (
        "assessment",
        "new_qualified_count",
        "new_distinct_source_role_count",
        "new_qualified_project_or_brand_count",
        "new_expression_pattern_count",
        "duplicate_rate",
        "assessment_basis",
    )
    if not isinstance(marginal, dict) or marginal.get("assessment") not in MARGINAL_GAIN or any(field not in marginal for field in required_gain):
        return result("invalid_marginal_information_gain", False)
    for field in required_gain[1:5]:
        if not nonnegative_number(marginal.get(field)):
            return result("invalid_marginal_information_gain", False, invalid_field=field)
    duplicate_rate = marginal.get("duplicate_rate")
    if duplicate_rate is not None and (not nonnegative_number(duplicate_rate) or duplicate_rate > 1):
        return result("invalid_marginal_information_gain", False, invalid_field="duplicate_rate")
    if not nonempty(marginal.get("assessment_basis")):
        return result("invalid_marginal_information_gain", False, invalid_field="assessment_basis")
    if receipt.get("failure_class") not in FAILURE_CLASSES or not nonempty(receipt.get("remaining_gap")) or not nonempty(receipt.get("stop_reason")):
        return result("invalid_receipt", False)
    for field in ("executed_result_batch_count", "actual_open_count"):
        if not nonnegative_number(receipt.get(field)):
            return result("invalid_receipt", False, invalid_field=field)

    learning_records = payload.get("query_learning_records")
    if not isinstance(learning_records, list):
        return result("invalid_query_learning_records", False)
    review_batches, invalid_reviews = validate_review_batches(payload.get("promotion_review_batches"))
    if invalid_reviews:
        return invalid_reviews
    if batch_state == "proposed_incremental_batch":
        if learning_records or receipt.get("executed_result_batch_count") != 0 or receipt.get("actual_open_count") != 0:
            return result("proposed_incremental_batch_must_be_unexecuted", False)
    else:
        record_ids = [record.get("query_id") for record in learning_records if isinstance(record, dict)]
        if len(record_ids) != len(set(record_ids)) or set(record_ids) != set(query_by_id):
            return result("query_learning_record_coverage_mismatch", False)
        for index, record in enumerate(learning_records):
            invalid = validate_learning_record(
                record,
                index,
                qualified_classes,
                query_by_id,
                review_batches,
                payload["business_question_family"],
            )
            if invalid:
                return invalid
        expected_batches = sum(record["result_batch_count"] for record in learning_records)
        expected_opens = sum(record["actual_open_count"] for record in learning_records)
        if receipt.get("executed_result_batch_count") != expected_batches or receipt.get("actual_open_count") != expected_opens:
            return result("receipt_execution_count_mismatch", False, expected_result_batches=expected_batches, expected_actual_opens=expected_opens)
        if receipt.get("evidence_sufficiency_status") == "sufficient":
            short = [
                record["query_id"]
                for record in learning_records
                if record["result_batch_count"] < query_by_id[record["query_id"]]["minimum_result_batches"]
                or record["actual_open_count"] < query_by_id[record["query_id"]]["minimum_actual_opens"]
            ]
            if short:
                return result("sufficient_claim_requires_query_execution_floors", False, short_query_ids=short)

    return result(
        "pass",
        True,
        task_id=payload["task_id"],
        business_question_ref=payload["business_question_ref"],
        business_question_family=payload["business_question_family"],
        batch_state=batch_state,
        acceptance_mode=acceptance_mode,
        evidence_sufficiency_status=receipt["evidence_sufficiency_status"],
        needs_downstream_authorization=needs_auth,
        query_learning_record_count=len(learning_records),
        promotion_review_batch_count=len(review_batches),
        adaptive_extension_authorized=extension.get("authorized") is True,
        incremental_execution_authorized=batch_state == "in_scope_iteration_batch" or (batch_state == "approved_incremental_batch" and extension.get("authorized") is True),
        live_channel_authorized=False,
        portable_channel_preflight_still_required=batch_state in {"approved_incremental_batch", "in_scope_iteration_batch"},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", type=Path)
    group.add_argument("--applicability-input", type=Path)
    args = parser.parse_args()
    path = args.applicability_input or args.input
    payload = json.loads(path.read_text(encoding="utf-8"))
    validation = validate_applicability(payload) if args.applicability_input else validate_package(payload)
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if validation["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
