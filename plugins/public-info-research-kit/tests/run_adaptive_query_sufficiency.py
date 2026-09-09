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


def completion_cases(validator, make_payload, applicability_schema):
    cases = []
    def check_package(name, payload, status="pass", passed=True):
        cases.append(check(name, validator.validate_package(payload, allow_legacy_unbound=True), status, passed))

    original = make_payload()
    original["receipt"]["evidence_sufficiency_status"] = "sufficient"
    check_package("status_only_cannot_prove_cumulative_completion", original,
                  "cumulative_evidence_required_for_sufficient_claim", False)

    complete = make_payload()
    contract = complete["consumer_contract"]
    contract["count_threshold"] = 5
    contract["diversity_requirements"] = {"minimum_project_or_brand_count": 3,
        "maximum_qualified_items_per_project_or_brand": 2, "minimum_independent_sources": 3}
    complete["receipt"].update(evidence_sufficiency_status="sufficient",
        remaining_gap="非关键补充图片仍缺，不影响本次已明确要求",
        cumulative_evidence=[{"evidence_item_id": identity,
            "project_or_brand_id": "project-"+str(index % 3),
            "source_id": "source-"+str(index % 3), "object_id": "subject"}
            for index, identity in enumerate(["reused-1", "reused-2", "reused-3", "new-1", "new-2"])],
        requirement_assessments={criterion: {"met": True, "basis": "上述累计材料支持本条件；包含本任务可复用的既有证据"}
            for criterion in contract["quality_criteria"]})
    check_package("three_reused_plus_two_new_meet_five", complete)
    check_package("noncritical_gap_does_not_block_sufficient_claim", complete)
    custom = copy.deepcopy(complete)
    custom["consumer_contract"]["diversity_requirements"]["覆盖业务所需视角"] = True
    custom["receipt"]["requirement_assessments"]["覆盖业务所需视角"] = {"met": True, "basis": "本任务累计证据已覆盖指定视角"}
    unchanged = copy.deepcopy(custom)
    check_package("nonnumeric_business_requirement_is_assessed", custom)
    cases.append(check("validation_preserves_original_requirements", {"status": "pass", "passed": custom == unchanged}, "pass", True))
    short = copy.deepcopy(complete)
    short["receipt"]["cumulative_evidence"] = short["receipt"]["cumulative_evidence"][-2:]
    check_package("two_cumulative_items_cannot_claim_five", short, "sufficiency_claim_contradicts_requirements", False)
    short["receipt"]["evidence_sufficiency_status"] = "partially_sufficient"
    check_package("two_valid_items_remain_deliverable_as_partial", short)

    duplicate = copy.deepcopy(complete)
    duplicate["receipt"]["cumulative_evidence"].append(copy.deepcopy(duplicate["receipt"]["cumulative_evidence"][0]))
    check_package("reused_duplicate_does_not_invalidate_valid_set", duplicate)
    duplicate["receipt"]["cumulative_evidence"] = duplicate["receipt"]["cumulative_evidence"][:4] + [duplicate["receipt"]["cumulative_evidence"][0]]
    check_package("duplicate_cannot_make_four_equal_five", duplicate, "sufficiency_claim_contradicts_requirements", False)
    reused = copy.deepcopy(complete)
    reused["receipt"]["cumulative_evidence"].append(dict(reused["receipt"]["cumulative_evidence"][0], reuse_note="在后续批次再次引用"))
    check_package("reuse_annotation_does_not_change_evidence_identity", reused)
    conflict = copy.deepcopy(complete)
    conflicting = dict(conflict["receipt"]["cumulative_evidence"][0], source_id="different-source")
    conflict["receipt"]["cumulative_evidence"].append(conflicting)
    check_package("conflicting_identity_is_not_double_counted", conflict, "cumulative_evidence_identity_conflict", False)

    for field, value in [("minimum_independent_sources", 4), ("minimum_project_or_brand_count", 4), ("maximum_qualified_items_per_project_or_brand", 1)]:
        payload = copy.deepcopy(complete); payload["consumer_contract"]["diversity_requirements"][field] = value
        check_package("hard_"+field+"_participates", payload, "sufficiency_claim_contradicts_requirements", False)
    objects = copy.deepcopy(complete); objects["consumer_contract"]["required_object_ids"] = ["subject"]
    check_package("explicit_required_object_is_covered", objects)
    objects["consumer_contract"]["required_object_ids"].append("missing-critical-object")
    check_package("critical_object_gap_rejects_only_completion", objects, "sufficiency_claim_contradicts_requirements", False)
    quality = copy.deepcopy(complete)
    quality["receipt"]["requirement_assessments"][quality["consumer_contract"]["quality_criteria"][0]]["met"] = False
    check_package("meeting_count_does_not_override_failed_quality", quality, "sufficiency_claim_contradicts_requirements", False)

    target = copy.deepcopy(short); target["receipt"]["evidence_sufficiency_status"] = "sufficient"
    target["consumer_contract"].pop("count_threshold"); target["consumer_contract"]["count_target"] = 5
    target["consumer_contract"]["diversity_requirements"] = {}
    target["consumer_contract"]["diversity_targets"] = {"minimum_independent_sources": 99}
    check_package("aspirational_count_and_diversity_are_not_hard_floors", target)
    target["consumer_contract"]["acceptance_mode"] = "quality_sufficiency"
    target["consumer_contract"].pop("count_target"); target["receipt"].pop("cumulative_evidence")
    check_package("quality_only_task_has_no_invented_count_floor", target)

    generic = make_payload()
    generic["consumer_contract"]["qualified_match_classes"] = ["original_report"]
    generic["consumer_contract"]["non_counted_match_classes"] = ["source_clue"]
    generic["consumer_contract"]["diversity_requirements"] = {"minimum_independent_sources": 3}
    for record in generic["query_learning_records"]:
        total = sum(record["qualification_counts"].values())
        record["qualification_counts"] = {"original_report": record["qualified_count"], "source_clue": total-record["qualified_count"]}
        record.pop("qualified_project_or_brand_count", None)
    generic["receipt"]["marginal_information_gain"] = {"assessment": "low", "assessment_basis": "本批来源重复，未增加关键论据"}
    check_package("generic_report_omits_inapplicable_legacy_counters", generic)
    generic["consumer_contract"]["marginal_gain_fields"] = ["new_qualified_count"]
    check_package("explicit_gain_requirement_cannot_disappear", generic, "invalid_marginal_information_gain", False)
    generic["receipt"]["marginal_information_gain"]["new_qualified_count"] = 0
    check_package("applicable_zero_gain_is_distinct_from_absence", generic)

    app = {"schema": applicability_schema, "task_id": "business-criteria",
        "route_receipt": {"primary_route_id": "ROUTE-OFFICIAL-RESOLVER", "required_gate_ids": ["GATE-D237-RESEARCH-SUFFICIENCY-DEFAULT"]},
        "acceptance_mode": "hybrid"}
    cases.append(check("mode_name_alone_is_not_research_criteria", validator.validate_applicability(app), "d237_consumer_contract_required", False))
    app.update(count_target=5, quality_criteria=["能回到原始报告的支持与反对论据"])
    cases.append(check("original_qualitative_goal_and_soft_target_are_usable", validator.validate_applicability(app), "pass", True))
    # Also reject a contradictory exemption supplied directly to the checker.
    direct = {'schema':applicability_schema, 'task_id':'explicit-direct-research',
        'route_receipt':{'primary_route_id':'ROUTE-WECHAT-KNOWN-URL','required_gate_ids':['GATE-D237-RESEARCH-SUFFICIENCY-DEFAULT']},
        'sufficiency_policy':'exempt_simple_direct_retrieval',
        'simple_direct_retrieval_exemption':{'exemption_type':'known_url_read','evidence_target':'https://example.com/article',
            'stop_condition':'Read the supplied article','human_authorization_ref':'received_task:explicit-direct-research'}}
    mandatory = {'count_threshold':5, 'quality_criteria':['支持原任务判断'],
        'diversity_requirements':{'minimum_independent_sources':3}, 'required_object_ids':['甲','乙']}
    for label, fields in [(key,{key:value}) for key,value in mandatory.items()] + [('combined',mandatory), ('nested_qualification',{'qualification_policy':mandatory})]:
        request = copy.deepcopy(direct); request.update(copy.deepcopy(fields))
        cases.append(check('explicit_exemption_cannot_erase_'+label, validator.validate_applicability(request), 'research_requirements_forbid_simple_exemption', False))
    optional = copy.deepcopy(direct); optional.update(count_target=5, diversity_targets={'minimum_independent_sources':3}, marginal_gain_fields=['new_qualified_count'])
    cases.append(check('optional_targets_do_not_forbid_direct_reading', validator.validate_applicability(optional), 'pass', True))
    return cases


# Historical structural fixtures intentionally use the explicit read-only API.
# Frozen-request and actual-execution requirements are covered by the binding runners.
def main() -> int:
    cases: list[dict] = []
    partial = load("golden-tasks/golden_research_partial.json")
    proposal = load("golden-tasks/golden_incremental_proposal.json")
    promotion = load("golden-tasks/golden_query_promotion.json")
    direct = load("golden-tasks/golden_direct_retrieval_exemption.json")

    cases.append(check("golden_initial_partial", MODULE.validate_package(partial, allow_legacy_unbound=True), "pass", True))
    cases.append(check("golden_incremental_proposal", MODULE.validate_package(proposal, allow_legacy_unbound=True), "pass", True))
    cases.append(check("golden_cross_task_promotion", MODULE.validate_package(promotion, allow_legacy_unbound=True), "pass", True))
    cases.append(check("golden_direct_retrieval_exemption", MODULE.validate_applicability(direct), "pass", True))
    cases.append(check("missing_acceptance_mode", MODULE.validate_applicability(load("negative-cases/d237_missing_acceptance_mode.json")), "d237_consumer_contract_required", False))
    cases.append(check("proposal_cannot_claim_authority", MODULE.validate_package(load("negative-cases/d237_proposal_claims_authority.json"), allow_legacy_unbound=True), "incremental_batch_authorization_mismatch", False))
    cases.append(check("one_task_cannot_be_recommended", MODULE.validate_package(load("negative-cases/d237_recommended_from_one_task.json"), allow_legacy_unbound=True), "recommended_query_cross_task_validation_insufficient", False))

    payload = copy.deepcopy(partial)
    payload["consumer_contract"]["acceptance_mode"] = "count_based"
    payload["consumer_contract"]["count_threshold"] = None
    cases.append(check("count_mode_requires_threshold", MODULE.validate_package(payload, allow_legacy_unbound=True), "count_threshold_required", False))

    payload = copy.deepcopy(partial)
    payload["consumer_contract"]["acceptance_mode"] = "quality_sufficiency"
    payload["consumer_contract"]["quality_criteria"] = []
    cases.append(check("quality_mode_requires_criteria", MODULE.validate_package(payload, allow_legacy_unbound=True), "quality_criteria_required", False))

    payload = copy.deepcopy(partial)
    payload["receipt"]["evidence_sufficiency_status"] = "queries_completed"
    cases.append(check("query_completion_is_not_sufficiency", MODULE.validate_package(payload, allow_legacy_unbound=True), "invalid_evidence_sufficiency_status", False))

    payload = copy.deepcopy(proposal)
    payload["batch"]["batch_state"] = "approved_incremental_batch"
    payload["receipt"]["needs_downstream_authorization"] = False
    cases.append(check("approved_increment_requires_authorization", MODULE.validate_package(payload, allow_legacy_unbound=True), "adaptive_extension_not_authorized", False))

    approved = approved_incremental()
    cases.append(check("approved_increment_with_limits", MODULE.validate_package(approved, allow_legacy_unbound=True), "pass", True))

    payload = copy.deepcopy(proposal)
    payload["query_learning_records"] = [copy.deepcopy(partial["query_learning_records"][0])]
    cases.append(check("proposal_must_remain_unexecuted", MODULE.validate_package(payload, allow_legacy_unbound=True), "proposed_incremental_batch_must_be_unexecuted", False))

    payload = copy.deepcopy(partial)
    payload["batch"]["queries"][0]["minimum_actual_opens"] = 0
    cases.append(check("query_execution_floor_must_be_positive", MODULE.validate_package(payload, allow_legacy_unbound=True), "invalid_query_execution_floor", False))

    payload = copy.deepcopy(partial)
    record = payload["query_learning_records"][0]
    record["result_batch_count"] = 1
    record["actual_open_count"] = 1
    record["failure_class"] = None
    payload["receipt"]["executed_result_batch_count"] = 1
    payload["receipt"]["actual_open_count"] = 1
    cases.append(check("floor_shortfall_needs_failure_attribution", MODULE.validate_package(payload, allow_legacy_unbound=True), "query_execution_floor_shortfall_unexplained", False))

    payload = copy.deepcopy(partial)
    record = payload["query_learning_records"][0]
    record["result_batch_count"] = 1
    record["actual_open_count"] = 1
    payload["receipt"]["executed_result_batch_count"] = 1
    payload["receipt"]["actual_open_count"] = 1
    payload["receipt"]["evidence_sufficiency_status"] = "sufficient"
    cases.append(check("sufficient_claim_requires_query_floors", MODULE.validate_package(payload, allow_legacy_unbound=True), "sufficient_claim_requires_query_execution_floors", False))

    payload = copy.deepcopy(partial)
    payload["query_learning_records"][0]["qualified_count"] = 3
    cases.append(check("qualified_count_is_recomputed", MODULE.validate_package(payload, allow_legacy_unbound=True), "qualified_count_mismatch", False))

    payload = copy.deepcopy(partial)
    payload["query_learning_records"][0]["qualified_rate"] = 1.0
    cases.append(check("qualified_rate_is_recomputed", MODULE.validate_package(payload, allow_legacy_unbound=True), "qualified_rate_mismatch", False))

    payload = copy.deepcopy(promotion)
    record = payload["query_learning_records"][0]
    record["attribution_status"] = "not_recorded_legacy_receipt"
    record["qualification_counts"] = {"direct": None, "excluded": None}
    record["qualified_count"] = None
    record["qualified_rate"] = None
    record["qualified_project_or_brand_count"] = None
    cases.append(check("unattributed_query_cannot_be_recommended", MODULE.validate_package(payload, allow_legacy_unbound=True), "recommended_query_attribution_missing", False))

    payload = copy.deepcopy(promotion)
    payload["promotion_review_batches"][0]["business_question_family"] = "其他业务问题族"
    cases.append(check("promotion_review_family_must_match", MODULE.validate_package(payload, allow_legacy_unbound=True), "recommended_query_review_family_mismatch", False))

    payload = copy.deepcopy(promotion)
    duplicate = copy.deepcopy(payload["promotion_review_batches"][0])
    duplicate["review_batch_id"] = "PROMOTION-REVIEW-002"
    payload["promotion_review_batches"].append(duplicate)
    cases.append(check("query_cannot_be_covered_twice", MODULE.validate_package(payload, allow_legacy_unbound=True), "promotion_review_query_covered_by_multiple_batches", False))

    applicability = {
        "schema": "query_sufficiency_applicability.v1",
        "task_id": "APP-DEFAULT-01",
        "route_receipt": {"primary_route_id": "ROUTE-XHS", "required_gate_ids": ["GATE-D237-RESEARCH-SUFFICIENCY-DEFAULT"]},
        "acceptance_mode": "hybrid",
        "count_threshold": 5, "quality_criteria": ["来源对应原问题"],
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

    cases.extend(completion_cases(MODULE, lambda: copy.deepcopy(partial), "query_sufficiency_applicability.v1"))

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
