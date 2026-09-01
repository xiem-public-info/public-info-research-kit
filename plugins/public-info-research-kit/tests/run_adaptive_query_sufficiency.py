#!/usr/bin/env python3
"""Offline golden and negative behavior checks for the public D-237 contract."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"
MODULE_PATH = ROOT / "tools/validate_adaptive_query_sufficiency.py"
SPEC = importlib.util.spec_from_file_location("validate_adaptive_query_sufficiency", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load(relative: str) -> dict:
    return json.loads((FIXTURES / relative).read_text(encoding="utf-8"))


def check(case_id: str, receipt: dict, expected_status: str, expected_passed: bool) -> dict:
    return {
        "case_id": case_id,
        "expected_status": expected_status,
        "actual_status": receipt.get("status"),
        "expected_passed": expected_passed,
        "actual_passed": receipt.get("passed"),
        "passed": receipt.get("status") == expected_status and receipt.get("passed") is expected_passed,
    }


def approved_incremental() -> dict:
    payload = load("golden-tasks/golden_incremental_proposal.json")
    payload["batch"]["batch_state"] = "approved_incremental_batch"
    payload["consumer_contract"]["adaptive_extension"] = {
        "authorized": True,
        "authorization_ref": "BUSINESS-OWNER-AUTH-01",
        "maximum_incremental_batches": 1,
        "time_limit_minutes": 30,
        "cost_limit": "manual_low_frequency_only",
    }
    payload["receipt"].update(
        {
            "evidence_sufficiency_status": "partially_sufficient",
            "needs_downstream_authorization": False,
            "failure_class": "content_supply_gap",
            "remaining_gap": "当前批次仍缺独立来源角色",
            "stop_reason": "授权的一个增量批次已执行完毕",
            "executed_result_batch_count": 2,
            "actual_open_count": 2,
        }
    )
    payload["receipt"]["marginal_information_gain"] = {
        "assessment": "low",
        "new_qualified_count": 1,
        "new_distinct_source_role_count": 1,
        "new_qualified_project_or_brand_count": 1,
        "new_expression_pattern_count": 0,
        "duplicate_rate": 0.5,
        "assessment_basis": "增量批次只补到一条合格反例，边际增益较低",
    }
    payload["query_learning_records"] = [
        {
            "query_id": "xhs-q02",
            "exact_query_text": "某城市 同类项目 入住后 好看不实用",
            "attribution_status": "recorded",
            "discovery_evidence_item_ids": ["EV-I-001"],
            "revisit_evidence_item_ids": [],
            "qualification_counts": {"direct": 1, "supporting": 0, "excluded": 1},
            "qualified_count": 1,
            "qualified_rate": 0.5,
            "qualified_project_or_brand_count": 1,
            "result_batch_count": 2,
            "actual_open_count": 2,
            "marginal_information_gain": "low",
            "effective_terms": ["入住后", "好看不实用"],
            "low_efficiency_terms": [],
            "identity_or_object_drift": [],
            "failure_class": "content_supply_gap",
            "stop_reason": "完成授权批次，仍缺来源角色多样性",
            "validated_task_count": 1,
            "recommended_query_status": "candidate",
            "human_review": {"status": "pending", "reviewer": None, "reviewed_at": None, "review_batch_id": None},
        }
    ]
    return payload


def main() -> int:
    cases: list[dict] = []
    partial = load("golden-tasks/golden_research_partial.json")
    proposal = load("golden-tasks/golden_incremental_proposal.json")
    promotion = load("golden-tasks/golden_query_promotion.json")
    direct = load("golden-tasks/golden_direct_retrieval_exemption.json")

    cases.append(check("golden_initial_partial", MODULE.validate_package(partial), "pass", True))
    cases.append(check("golden_incremental_proposal", MODULE.validate_package(proposal), "pass", True))
    cases.append(check("golden_cross_task_promotion", MODULE.validate_package(promotion), "pass", True))
    cases.append(check("golden_direct_retrieval_exemption", MODULE.validate_applicability(direct), "pass", True))
    cases.append(check("missing_acceptance_mode", MODULE.validate_applicability(load("negative-cases/d237_missing_acceptance_mode.json")), "d237_consumer_contract_required", False))
    cases.append(check("proposal_cannot_claim_authority", MODULE.validate_package(load("negative-cases/d237_proposal_claims_authority.json")), "incremental_batch_authorization_mismatch", False))
    cases.append(check("one_task_cannot_be_recommended", MODULE.validate_package(load("negative-cases/d237_recommended_from_one_task.json")), "recommended_query_cross_task_validation_insufficient", False))

    payload = copy.deepcopy(partial)
    payload["consumer_contract"]["acceptance_mode"] = "count_based"
    payload["consumer_contract"]["count_threshold"] = None
    cases.append(check("count_mode_requires_threshold", MODULE.validate_package(payload), "count_threshold_required", False))

    payload = copy.deepcopy(partial)
    payload["consumer_contract"]["acceptance_mode"] = "quality_sufficiency"
    payload["consumer_contract"]["quality_criteria"] = []
    cases.append(check("quality_mode_requires_criteria", MODULE.validate_package(payload), "quality_criteria_required", False))

    payload = copy.deepcopy(partial)
    payload["receipt"]["evidence_sufficiency_status"] = "queries_completed"
    cases.append(check("query_completion_is_not_sufficiency", MODULE.validate_package(payload), "invalid_evidence_sufficiency_status", False))

    payload = copy.deepcopy(proposal)
    payload["batch"]["batch_state"] = "approved_incremental_batch"
    payload["receipt"]["needs_downstream_authorization"] = False
    cases.append(check("approved_increment_requires_authorization", MODULE.validate_package(payload), "adaptive_extension_not_authorized", False))

    approved = approved_incremental()
    cases.append(check("approved_increment_with_limits", MODULE.validate_package(approved), "pass", True))

    payload = copy.deepcopy(proposal)
    payload["query_learning_records"] = [copy.deepcopy(partial["query_learning_records"][0])]
    cases.append(check("proposal_must_remain_unexecuted", MODULE.validate_package(payload), "proposed_incremental_batch_must_be_unexecuted", False))

    payload = copy.deepcopy(partial)
    payload["batch"]["queries"][0]["minimum_actual_opens"] = 0
    cases.append(check("query_execution_floor_must_be_positive", MODULE.validate_package(payload), "invalid_query_execution_floor", False))

    payload = copy.deepcopy(partial)
    record = payload["query_learning_records"][0]
    record["result_batch_count"] = 1
    record["actual_open_count"] = 1
    record["failure_class"] = None
    payload["receipt"]["executed_result_batch_count"] = 1
    payload["receipt"]["actual_open_count"] = 1
    cases.append(check("floor_shortfall_needs_failure_attribution", MODULE.validate_package(payload), "query_execution_floor_shortfall_unexplained", False))

    payload = copy.deepcopy(partial)
    record = payload["query_learning_records"][0]
    record["result_batch_count"] = 1
    record["actual_open_count"] = 1
    payload["receipt"]["executed_result_batch_count"] = 1
    payload["receipt"]["actual_open_count"] = 1
    payload["receipt"]["evidence_sufficiency_status"] = "sufficient"
    cases.append(check("sufficient_claim_requires_query_floors", MODULE.validate_package(payload), "sufficient_claim_requires_query_execution_floors", False))

    payload = copy.deepcopy(partial)
    payload["query_learning_records"][0]["qualified_count"] = 3
    cases.append(check("qualified_count_is_recomputed", MODULE.validate_package(payload), "qualified_count_mismatch", False))

    payload = copy.deepcopy(partial)
    payload["query_learning_records"][0]["qualified_rate"] = 1.0
    cases.append(check("qualified_rate_is_recomputed", MODULE.validate_package(payload), "qualified_rate_mismatch", False))

    payload = copy.deepcopy(promotion)
    record = payload["query_learning_records"][0]
    record["attribution_status"] = "not_recorded_legacy_receipt"
    record["qualification_counts"] = {"direct": None, "excluded": None}
    record["qualified_count"] = None
    record["qualified_rate"] = None
    record["qualified_project_or_brand_count"] = None
    cases.append(check("unattributed_query_cannot_be_recommended", MODULE.validate_package(payload), "recommended_query_attribution_missing", False))

    payload = copy.deepcopy(promotion)
    payload["promotion_review_batches"][0]["business_question_family"] = "其他业务问题族"
    cases.append(check("promotion_review_family_must_match", MODULE.validate_package(payload), "recommended_query_review_family_mismatch", False))

    payload = copy.deepcopy(promotion)
    duplicate = copy.deepcopy(payload["promotion_review_batches"][0])
    duplicate["review_batch_id"] = "PROMOTION-REVIEW-002"
    payload["promotion_review_batches"].append(duplicate)
    cases.append(check("query_cannot_be_covered_twice", MODULE.validate_package(payload), "promotion_review_query_covered_by_multiple_batches", False))

    applicability = {
        "schema": "query_sufficiency_applicability.v1",
        "task_id": "APP-DEFAULT-01",
        "route_receipt": {"primary_route_id": "ROUTE-XHS", "required_gate_ids": ["GATE-D237-RESEARCH-SUFFICIENCY-DEFAULT"]},
        "acceptance_mode": "hybrid",
        "research_characteristics": ["multiple_independent_queries"],
    }
    receipt = MODULE.validate_applicability(applicability)
    cases.append(check("omitted_policy_defaults_to_d237", receipt, "pass", True))
    cases[-1]["passed"] = cases[-1]["passed"] and receipt.get("defaulted_from_omission") is True

    payload = copy.deepcopy(direct)
    payload["research_characteristics"] = ["support_and_counterevidence_required"]
    cases.append(check("research_cannot_hide_as_direct_retrieval", MODULE.validate_applicability(payload), "research_characteristics_forbid_simple_exemption", False))

    non_retrieval = {
        "schema": "query_sufficiency_applicability.v1",
        "task_id": "APP-NON-01",
        "route_receipt": {"primary_route_id": "ROUTE-DOCS", "required_gate_ids": []},
    }
    cases.append(check("non_retrieval_is_not_applicable", MODULE.validate_applicability(non_retrieval), "not_applicable_non_retrieval_task", True))

    report = {
        "schema": "adaptive_query_sufficiency_fixture_report.v1",
        "status": "pass" if all(row["passed"] for row in cases) else "fail",
        "case_count": len(cases),
        "failure_count": sum(not row["passed"] for row in cases),
        "cases": cases,
        "platform_opened": False,
        "external_write_executed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
