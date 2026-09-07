#!/usr/bin/env python3
"""Offline positive and negative fixtures for portable D-292 behavior."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/validate_d292_research_orchestration.py"
VALID_PATH = ROOT / "tests/fixtures/d292-research-orchestration/valid.json"
SPEC = importlib.util.spec_from_file_location("validate_d292", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def run_case(case_id: str, contract: dict, expected_pass: bool, expected_error: str | None = None) -> dict:
    result = MODULE.validate(contract)
    matched = result["passed"] is expected_pass and (expected_error is None or expected_error in result["errors"])
    return {
        "case_id": case_id,
        "expected_pass": expected_pass,
        "actual_pass": result["passed"],
        "expected_error": expected_error,
        "passed": matched,
    }


def main() -> int:
    valid = json.loads(VALID_PATH.read_text(encoding="utf-8"))
    cases = [run_case("valid_d292_orchestration", valid, True)]

    row = copy.deepcopy(valid)
    row["aggregate_surfaces"][0]["aggregate_surface_id"] = "xhs_ask_diandian"
    cases.append(run_case("platform_surfaces_remain_distinct", row, False, "aggregate_surfaces[0]_platform_surface_identity_mismatch"))

    row = copy.deepcopy(valid)
    row["aggregate_surfaces"][0]["aggregate_answer_evidence_allowed"] = True
    cases.append(run_case("aggregate_answer_cannot_be_evidence", row, False, "aggregate_surfaces[0]_aggregate_answer_evidence_forbidden"))

    row = copy.deepcopy(valid)
    row["competitor_lifecycle_precheck"]["objects"][0]["delivery_date_checked"] = False
    cases.append(run_case("delivery_date_must_be_checked", row, False, "competitor_lifecycle_precheck.objects[0]_delivery_date_checked_required"))

    row = copy.deepcopy(valid)
    row["competitor_lifecycle_precheck"]["objects"][0]["recommended_role"] = "deep_search"
    cases.append(run_case("under_12_months_is_tail_end_reference", row, False, "competitor_lifecycle_precheck.objects[0]_delivery_under_12_months_requires_tail_end_reference"))

    row = copy.deepcopy(valid)
    row["complete_event_count_policy"]["target_is_maximum"] = True
    cases.append(run_case("target_is_not_a_cap", row, False, "target_is_not_maximum_and_qualified_excess_must_be_preserved"))

    row = copy.deepcopy(valid)
    row["complete_event_count_policy"]["unique_household_journey_count"] = 7
    cases.append(run_case("global_journey_count_is_deduplicated", row, False, "unique_household_journey_count_cannot_exceed_project_affiliations"))

    row = copy.deepcopy(valid)
    row["first_return"]["merged_increment_proposal"]["proposed"] = False
    cases.append(run_case("partial_core_requires_one_merged_proposal", row, False, "incomplete_semantic_core_requires_one_merged_increment_proposal"))

    row = copy.deepcopy(valid)
    row["first_return"]["merged_increment_proposal"]["execution_authorized"] = True
    cases.append(run_case("increment_proposal_cannot_self_authorize", row, False, "merged_increment_cannot_self_authorize"))

    row = copy.deepcopy(valid)
    row["official_expression_policy"]["necessary_original_wording_required"] = False
    cases.append(run_case("official_expression_keeps_necessary_wording", row, False, "official_expression_requires_core_view_wording_and_source"))

    row = copy.deepcopy(valid)
    row["thread_policy"]["rotate_thread_after_close"] = True
    cases.append(run_case("thread_rotates_only_after_natural_close", row, False, "thread_rotation_before_natural_close_forbidden"))

    ordinary = copy.deepcopy(valid)
    ordinary["competitor_lifecycle_precheck"] = {"applies": False}
    ordinary["complete_event_count_policy"] = {"applies": False}
    ordinary["official_expression_policy"] = {"applies": False}
    ordinary["first_return"] = {"residential_semantic_core_applies": False, "semantic_core_support_status": "not_applicable", "merged_increment_proposal": {"proposed": False, "downstream_authorization_required": True, "execution_authorized": False}}
    cases.append(run_case("customer_concerns_without_complete_events", ordinary, True))
    ordinary["first_return"]["merged_increment_proposal"]["execution_authorized"] = True
    cases.append(run_case("generic_research_cannot_self_authorize_extension", ordinary, False, "merged_increment_cannot_self_authorize"))
    report = {
        "schema": "d292_research_orchestration_fixture_report.v1",
        "status": "pass" if all(row["passed"] for row in cases) else "fail",
        "case_count": len(cases),
        "failure_count": sum(not row["passed"] for row in cases),
        "cases": cases,
        "offline_only": True,
        "live_authority_expanded": False,
        "platform_opened": False,
        "network_accessed": False,
        "external_write_executed": False
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
