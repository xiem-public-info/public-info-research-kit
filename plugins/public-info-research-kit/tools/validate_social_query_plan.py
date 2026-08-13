#!/usr/bin/env python3
"""Validate a D-235 social query plan and report all structural gaps at once."""

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
SURFACES = {
    "wechat": {"微信全局文章结果", "公众号文章列表", "公众号号内搜索", "微信AI搜索线索"},
    "xhs": {"小红书笔记列表", "小红书点点聚合线索"},
}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(plan: dict[str, Any], lexicon: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if plan.get("schema") != "social_query_plan.v1":
        errors.append("schema must be social_query_plan.v1")
    for field in ("task_id", "subject", "business_question", "plan_version", "stop_condition"):
        if not nonempty(plan.get(field)):
            errors.append(f"missing or empty field: {field}")
    mode = plan.get("searcher_mode")
    if mode not in MODES:
        errors.append("searcher_mode must be researcher, creator_supply_side, or tool_or_automation")
    if mode != "researcher":
        warnings.append("business research normally uses searcher_mode=researcher")

    allowed_atoms = {
        f"{family}:{atom}"
        for family, row in (lexicon.get("atom_families") or {}).items()
        for atom in row.get("atoms") or []
    }
    queries = plan.get("queries")
    if not isinstance(queries, list) or not queries:
        errors.append("queries must be a non-empty list")
        queries = []
    seen: set[str] = set()
    for index, row in enumerate(queries):
        prefix = f"queries[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        query_id = row.get("query_id")
        if not nonempty(query_id):
            errors.append(f"{prefix}.query_id is required")
        elif query_id in seen:
            errors.append(f"duplicate query_id: {query_id}")
        else:
            seen.add(query_id)
        platform = row.get("platform")
        if platform not in PLATFORMS:
            errors.append(f"{prefix}.platform must be wechat or xhs")
        surface = row.get("surface")
        if platform in PLATFORMS and surface not in SURFACES[platform]:
            errors.append(f"{prefix}.surface is not valid for {platform}")
        if not nonempty(row.get("exact_query_text")):
            errors.append(f"{prefix}.exact_query_text is required")
        if row.get("term_provenance") not in PROVENANCE:
            errors.append(f"{prefix}.term_provenance is invalid")
        if not nonempty(row.get("reading_target")):
            errors.append(f"{prefix}.reading_target is required")
        signature = row.get("atom_signature")
        if not isinstance(signature, list) or not signature:
            errors.append(f"{prefix}.atom_signature must be a non-empty list")
        else:
            for atom in signature:
                if atom not in allowed_atoms:
                    errors.append(f"{prefix}.atom_signature contains unknown atom: {atom}")

    return {
        "schema": "social_query_plan_validation.v1",
        "status": "pass" if not errors else "fail",
        "query_count": len(queries),
        "errors": errors,
        "warnings": warnings,
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
