#!/usr/bin/env python3
"""Validate the portable D-235 social query plan and its execution boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "resources/social_semantic_query_lexicon.v0.1.json"
MODES = {"researcher", "creator_supply_side", "tool_or_automation"}
PLATFORMS = {"wechat", "xhs"}
PROVENANCE = {"official_name", "business_judgment", "platform_suggestion", "aggregate_clue", "title", "body", "comment"}
ACCEPTANCE_MODES = {"d237_required", "exempt_simple_direct_retrieval"}
SURFACES = {
    "wechat": {"微信全局文章结果", "公众号文章列表", "公众号号内搜索", "微信AI搜索线索"},
    "xhs": {"小红书笔记列表", "小红书点点聚合线索"},
}
TOP_LEVEL_FIELDS = {
    "schema",
    "task_id",
    "subject",
    "identity_closure",
    "business_question",
    "business_question_family",
    "judgment_gap",
    "searcher_mode",
    "plan_version",
    "acceptance_mode",
    "acceptance",
    "adaptive_extension",
    "queries",
    "stop_condition",
}
QUERY_FIELDS = {
    "query_id",
    "platform",
    "surface",
    "exact_query_text",
    "execution_state",
    "phase",
    "query_hypothesis",
    "atom_signature",
    "term_provenance",
    "source_role_targets",
    "reading_target",
    "minimum_result_batches",
    "minimum_actual_opens",
    "expected_information_gain",
    "failure_attribution_required",
}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def nonempty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(nonempty(item) for item in value)


def validate(plan: dict[str, Any], lexicon: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if plan.get("schema") != "social_query_plan.v1":
        errors.append("schema must be social_query_plan.v1")
    unknown_top = sorted(set(plan) - TOP_LEVEL_FIELDS)
    if unknown_top:
        errors.append("unknown top-level fields: " + ", ".join(unknown_top))
    for field in (
        "task_id",
        "subject",
        "business_question",
        "business_question_family",
        "judgment_gap",
        "plan_version",
        "stop_condition",
    ):
        if not nonempty(plan.get(field)):
            errors.append(f"missing or empty field: {field}")

    identity = plan.get("identity_closure")
    identity_closed = False
    if not isinstance(identity, dict):
        errors.append("identity_closure must be an object")
    else:
        allowed = {"status", "city", "official_name", "phase_scope", "aliases_tested", "conflict_notes"}
        unknown = sorted(set(identity) - allowed)
        if unknown:
            errors.append("identity_closure has unknown fields: " + ", ".join(unknown))
        for field in ("city", "official_name", "phase_scope"):
            if not nonempty(identity.get(field)):
                errors.append(f"identity_closure.{field} is required")
        for field in ("aliases_tested", "conflict_notes"):
            value = identity.get(field)
            if not isinstance(value, list) or not all(nonempty(item) for item in value):
                errors.append(f"identity_closure.{field} must be a string list")
        if identity.get("status") == "closed":
            identity_closed = True
        elif identity.get("status") == "ambiguous":
            errors.append("identity_closure must be closed before query execution")
        else:
            errors.append("identity_closure.status must be closed or ambiguous")

    mode = plan.get("searcher_mode")
    if mode not in MODES:
        errors.append("searcher_mode must be researcher, creator_supply_side, or tool_or_automation")
    if mode != "researcher":
        warnings.append("business research normally uses searcher_mode=researcher")

    acceptance_mode = plan.get("acceptance_mode")
    if acceptance_mode not in ACCEPTANCE_MODES:
        errors.append("acceptance_mode is invalid")
    acceptance = plan.get("acceptance")
    if not isinstance(acceptance, dict):
        errors.append("acceptance must be an object")
        acceptance = {}
    else:
        allowed = {
            "quality_criteria",
            "minimum_qualified_items",
            "diversity_targets",
            "global_stop_condition",
            "exemption_reason",
            "direct_retrieval_target",
        }
        unknown = sorted(set(acceptance) - allowed)
        if unknown:
            errors.append("acceptance has unknown fields: " + ", ".join(unknown))
    if not nonempty_string_list(acceptance.get("quality_criteria")):
        errors.append("acceptance.quality_criteria must be a non-empty string list")
    if not positive_integer(acceptance.get("minimum_qualified_items")):
        errors.append("acceptance.minimum_qualified_items must be a positive integer")
    if not nonempty_string_list(acceptance.get("diversity_targets")):
        errors.append("acceptance.diversity_targets must be a non-empty string list")
    if not nonempty(acceptance.get("global_stop_condition")):
        errors.append("acceptance.global_stop_condition is required")
    if acceptance_mode == "exempt_simple_direct_retrieval":
        if not nonempty(acceptance.get("exemption_reason")) or not nonempty(acceptance.get("direct_retrieval_target")):
            errors.append("simple direct retrieval exemption requires exemption_reason and direct_retrieval_target")
        warnings.append("simple direct retrieval exemption is narrow and must not be used for comparison or generalization")

    adaptive = plan.get("adaptive_extension")
    adaptive_authorized = False
    if not isinstance(adaptive, dict):
        errors.append("adaptive_extension must be an object")
        adaptive = {}
    else:
        allowed = {"authorized", "authorized_by", "maximum_additional_queries"}
        unknown = sorted(set(adaptive) - allowed)
        if unknown:
            errors.append("adaptive_extension has unknown fields: " + ", ".join(unknown))
        adaptive_authorized = adaptive.get("authorized") is True
        maximum = adaptive.get("maximum_additional_queries")
        if adaptive_authorized:
            if adaptive.get("authorized_by") not in {"end_user", "downstream_business_owner"}:
                errors.append("authorized adaptive_extension requires authorized_by")
            if not positive_integer(maximum):
                errors.append("authorized adaptive_extension requires a positive maximum_additional_queries")
        else:
            if adaptive.get("authorized") is not False:
                errors.append("adaptive_extension.authorized must be boolean")
            if adaptive.get("authorized_by") is not None or maximum != 0:
                errors.append("unauthorized adaptive_extension must use authorized_by=null and maximum_additional_queries=0")

    allowed_atoms = {
        f"{family}:{atom}"
        for family, row in (lexicon.get("atom_families") or {}).items()
        for atom in row.get("atoms") or []
    }
    queries = plan.get("queries")
    if not isinstance(queries, list) or not queries:
        errors.append("queries must be a non-empty list")
        queries = []
    if acceptance_mode == "exempt_simple_direct_retrieval" and len(queries) != 1:
        errors.append("simple direct retrieval exemption requires exactly one query")

    seen_ids: set[str] = set()
    seen_exact: set[tuple[str, str]] = set()
    executable_query_ids: list[str] = []
    proposed_incremental_query_ids: list[str] = []
    for index, row in enumerate(queries):
        prefix = f"queries[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        unknown = sorted(set(row) - QUERY_FIELDS)
        if unknown:
            errors.append(f"{prefix} has unknown fields: {', '.join(unknown)}")
        query_id = row.get("query_id")
        if not nonempty(query_id):
            errors.append(f"{prefix}.query_id is required")
        elif query_id in seen_ids:
            errors.append(f"duplicate query_id: {query_id}")
        else:
            seen_ids.add(query_id)
        platform = row.get("platform")
        if platform not in PLATFORMS:
            errors.append(f"{prefix}.platform must be wechat or xhs")
        surface = row.get("surface")
        if platform in PLATFORMS and surface not in SURFACES[platform]:
            errors.append(f"{prefix}.surface is not valid for {platform}")
        exact = row.get("exact_query_text")
        if not nonempty(exact):
            errors.append(f"{prefix}.exact_query_text is required")
        elif platform in PLATFORMS:
            identity = (platform, exact.strip())
            if identity in seen_exact:
                errors.append(f"duplicate exact_query_text for {platform}: {exact}")
            else:
                seen_exact.add(identity)
        state = row.get("execution_state")
        if state == "frozen":
            if nonempty(query_id):
                executable_query_ids.append(query_id)
        elif state == "proposed_incremental":
            if nonempty(query_id):
                proposed_incremental_query_ids.append(query_id)
            warnings.append(f"{prefix} is proposal-only and cannot execute until authorized and frozen")
        else:
            errors.append(f"{prefix}.execution_state must be frozen or proposed_incremental")
        for field in ("phase", "query_hypothesis", "reading_target", "expected_information_gain"):
            if not nonempty(row.get(field)):
                errors.append(f"{prefix}.{field} is required")
        if row.get("term_provenance") not in PROVENANCE:
            errors.append(f"{prefix}.term_provenance is invalid")
        if not nonempty_string_list(row.get("source_role_targets")):
            errors.append(f"{prefix}.source_role_targets must be a non-empty string list")
        for field in ("minimum_result_batches", "minimum_actual_opens"):
            if not positive_integer(row.get(field)):
                errors.append(f"{prefix}.{field} must be a positive integer")
        if row.get("failure_attribution_required") is not True:
            errors.append(f"{prefix}.failure_attribution_required must be true")
        signature = row.get("atom_signature")
        if not isinstance(signature, list) or not signature:
            errors.append(f"{prefix}.atom_signature must be a non-empty list")
        else:
            for atom in signature:
                if atom not in allowed_atoms:
                    errors.append(f"{prefix}.atom_signature contains unknown atom: {atom}")

    if not executable_query_ids:
        warnings.append("plan has no frozen executable queries")
    if proposed_incremental_query_ids and not adaptive_authorized:
        warnings.append("adaptive_extension is not authorized; all incremental proposals remain non-executable")

    return {
        "schema": "social_query_plan_validation.v2",
        "status": "pass" if not errors else "fail",
        "query_count": len(queries),
        "identity_closed": identity_closed,
        "acceptance_mode": acceptance_mode,
        "adaptive_extension_authorized": adaptive_authorized,
        "executable_query_ids": executable_query_ids,
        "proposed_incremental_query_ids": proposed_incremental_query_ids,
        "errors": errors,
        "warnings": warnings,
        "portable_channel_preflight_required_before_gui_execution": True,
        "platform_opened": False,
        "network_accessed": False,
        "writes_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--lexicon", type=Path, default=LEXICON)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    lexicon = json.loads(args.lexicon.read_text(encoding="utf-8"))
    result = validate(plan, lexicon)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
