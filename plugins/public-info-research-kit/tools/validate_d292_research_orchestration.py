#!/usr/bin/env python3
"""Validate portable D-292 research orchestration and non-expansion boundaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_adaptive_query_sufficiency import validate_package


EXPECTED_SURFACES = {
    "wechat": "wechat_ai_search",
    "xhs": "xhs_ask_diandian",
}
WECHAT_ORIGINAL_SURFACES = {
    "wechat_global_article_results",
    "public_account_article_list",
    "public_account_internal_search",
    "known_public_article_url",
}
XHS_ORIGINAL_SURFACES = {
    "xhs_note_list",
    "xhs_visible_note_body",
    "xhs_visible_comment",
}


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate(contract: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if contract.get("schema") != "d292_research_orchestration.v1":
        errors.append("schema_invalid")
    if not _nonempty(contract.get("task_id")):
        errors.append("task_id_required")

    surfaces = contract.get("aggregate_surfaces")
    seen: set[tuple[str, str]] = set()
    if not isinstance(surfaces, list):
        errors.append("aggregate_surfaces_must_be_list")
        surfaces = []
    for index, row in enumerate(surfaces):
        prefix = f"aggregate_surfaces[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix}_must_be_object")
            continue
        platform = row.get("platform")
        surface_id = row.get("aggregate_surface_id")
        if platform not in EXPECTED_SURFACES or surface_id != EXPECTED_SURFACES.get(platform):
            errors.append(f"{prefix}_platform_surface_identity_mismatch")
        identity = (str(platform), str(surface_id))
        if identity in seen:
            errors.append(f"{prefix}_duplicate_surface")
        seen.add(identity)
        if row.get("authorization_status") not in {"authorized", "not_authorized", "unresolved"}:
            errors.append(f"{prefix}_authorization_status_invalid")
        if row.get("aggregate_output_role") != "ai_aggregate_clue":
            errors.append(f"{prefix}_aggregate_output_must_be_clue")
        if row.get("aggregate_answer_evidence_allowed") is not False:
            errors.append(f"{prefix}_aggregate_answer_evidence_forbidden")
        original = row.get("ordinary_original_source_surfaces")
        allowed = WECHAT_ORIGINAL_SURFACES if platform == "wechat" else XHS_ORIGINAL_SURFACES
        if not isinstance(original, list) or not original or any(item not in allowed for item in original):
            errors.append(f"{prefix}_ordinary_original_source_required")

    lifecycle = contract.get("competitor_lifecycle_precheck")
    if not isinstance(lifecycle, dict):
        errors.append("competitor_lifecycle_precheck_required")
        lifecycle = {}
    if lifecycle.get("applies") is not False:
        if lifecycle.get("complete_before_deep_retrieval") is not True:
            errors.append("lifecycle_precheck_must_precede_deep_retrieval")
        if lifecycle.get("downstream_decides_final_competitor_role") is not True:
            errors.append("downstream_competitor_authority_required")
        objects = lifecycle.get("objects")
        if lifecycle.get("applies") is True and (not isinstance(objects, list) or not objects):
            errors.append("lifecycle_objects_required")
        for index, row in enumerate(objects or []):
            prefix = f"competitor_lifecycle_precheck.objects[{index}]"
            if not isinstance(row, dict) or not _nonempty(row.get("object_id")):
                errors.append(f"{prefix}_object_id_required")
                continue
            for field in (
                "identity_closed",
                "current_new_home_supply_checked",
                "recent_six_month_content_checked",
                "launch_and_actual_product_checked",
                "delivery_date_checked",
            ):
                if row.get(field) is not True:
                    errors.append(f"{prefix}_{field}_required")
            months = row.get("months_to_delivery")
            if months != "unknown" and not isinstance(months, int):
                errors.append(f"{prefix}_months_to_delivery_invalid")
            if isinstance(months, int) and 0 <= months < 12 and row.get("recommended_role") != "tail_end_reference":
                errors.append(f"{prefix}_delivery_under_12_months_requires_tail_end_reference")
            if row.get("applicable_product_scope") not in {"whole_project", "partial_tier", "unknown"}:
                errors.append(f"{prefix}_applicable_product_scope_invalid")
            if row.get("recommended_role") not in {"deep_search", "partial_tier", "tail_end_reference", "exclude_candidate"}:
                errors.append(f"{prefix}_recommended_role_invalid")

    counts = contract.get("complete_event_count_policy")
    if not isinstance(counts, dict):
        errors.append("complete_event_count_policy_required")
        counts = {}
    if counts.get("applies") is not False:
        for field in (
            "minimum_per_project",
            "target_per_project",
            "project_event_affiliation_count",
            "unique_household_journey_count",
        ):
            if not _nonnegative_int(counts.get(field)):
                errors.append(f"{field}_must_be_nonnegative_integer")
        minimum = counts.get("minimum_per_project")
        target = counts.get("target_per_project")
        if _nonnegative_int(minimum) and _nonnegative_int(target) and target < minimum:
            errors.append("target_per_project_cannot_be_below_minimum")
        if counts.get("target_is_maximum") is not False or counts.get("preserve_qualified_excess") is not True:
            errors.append("target_is_not_maximum_and_qualified_excess_must_be_preserved")
        if counts.get("global_dedup_unit") != "independent_person_or_household_journey":
            errors.append("global_household_journey_dedup_required")
        affiliations = counts.get("project_event_affiliation_count")
        journeys = counts.get("unique_household_journey_count")
        if _nonnegative_int(affiliations) and _nonnegative_int(journeys) and journeys > affiliations:
            errors.append("unique_household_journey_count_cannot_exceed_project_affiliations")

    first_return = contract.get("first_return")
    if not isinstance(first_return, dict):
        errors.append("first_return_required")
        first_return = {}
    if first_return.get("residential_semantic_core_applies") is not False:
        for field in (
            "project_fact_support_assessed",
            "competitor_relation_support_assessed",
            "customer_choice_support_assessed",
            "counterexample_support_assessed",
        ):
            if first_return.get(field) is not True:
                errors.append(f"first_return_{field}_required")
    support = first_return.get("semantic_core_support_status")
    if support not in ({"not_applicable"} if first_return.get("residential_semantic_core_applies") is False else {"supported", "partial", "unsupported"}):
        errors.append("semantic_core_support_status_invalid")
    proposal = first_return.get("merged_increment_proposal")
    if not isinstance(proposal, dict):
        errors.append("merged_increment_proposal_required")
        proposal = {}
    if support in {"partial", "unsupported"} and proposal.get("proposed") is not True:
        errors.append("incomplete_semantic_core_requires_one_merged_increment_proposal")
    iteration = contract.get("in_scope_iteration_package")
    in_scope = isinstance(iteration, dict) and iteration.get("task_id") == contract.get("task_id") and iteration.get("batch", {}).get("batch_state") == "in_scope_iteration_batch" and validate_package(iteration)["passed"]
    if iteration is not None and not in_scope:
        errors.append("invalid_in_scope_iteration_package")
    if proposal.get("downstream_authorization_required") is not (False if in_scope else True):
        errors.append("merged_increment_requires_downstream_authorization")
    if proposal.get("execution_authorized") is not in_scope:
        errors.append("merged_increment_cannot_self_authorize")

    official = contract.get("official_expression_policy")
    if not isinstance(official, dict) or (official.get("applies") is not False and any(
        official.get(field) is not True
        for field in ("core_view_required", "necessary_original_wording_required", "source_locator_required")
    )):
        errors.append("official_expression_requires_core_view_wording_and_source")

    thread = contract.get("thread_policy")
    if not isinstance(thread, dict):
        errors.append("thread_policy_required")
        thread = {}
    naturally_closed = thread.get("current_retrieval_task_naturally_closed")
    rotate = thread.get("rotate_thread_after_close")
    if naturally_closed is not True and rotate is True:
        errors.append("thread_rotation_before_natural_close_forbidden")
    if thread.get("urge_or_interleave_next_batch") is not False:
        errors.append("urge_or_interleave_next_batch_forbidden")

    return {
        "schema": "d292_research_orchestration_validation.v1",
        "status": "pass" if not errors else "fail",
        "passed": not errors,
        "task_id": contract.get("task_id"),
        "aggregate_surface_count": len(surfaces),
        "errors": errors,
        "live_authority_expanded": False,
        "incremental_execution_authorized": in_scope and not errors,
        "platform_opened": False,
        "network_accessed": False,
        "external_write_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    result = validate(contract)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
