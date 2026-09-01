#!/usr/bin/env python3
"""Offline fixtures for the expanded public social query plan."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/social_query_plan.example.json"
LEXICON = ROOT / "resources/social_semantic_query_lexicon.v0.1.json"
MODULE_PATH = ROOT / "tools/validate_social_query_plan.py"
SPEC = importlib.util.spec_from_file_location("validate_social_query_plan", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def case(case_id: str, plan: dict, expected_status: str, assertion) -> dict:
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))
    result = MODULE.validate(plan, lexicon)
    matched = result["status"] == expected_status and assertion(result)
    return {
        "case_id": case_id,
        "expected_status": expected_status,
        "actual_status": result["status"],
        "passed": matched,
    }


def main() -> int:
    valid = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    cases = [
        case("valid_complete_plan", valid, "pass", lambda row: len(row["executable_query_ids"]) == 2),
    ]

    plan = copy.deepcopy(valid)
    plan["identity_closure"]["status"] = "ambiguous"
    cases.append(case("identity_must_close", plan, "fail", lambda row: row["identity_closed"] is False))

    plan = copy.deepcopy(valid)
    plan["queries"][0]["atom_signature"].append("unknown_family:unknown_atom")
    cases.append(case("unknown_semantic_atom_rejected", plan, "fail", lambda row: bool(row["errors"])))

    plan = copy.deepcopy(valid)
    plan["queries"][1]["execution_state"] = "proposed_incremental"
    cases.append(case("incremental_proposal_remains_non_executable", plan, "pass", lambda row: row["proposed_incremental_query_ids"] == ["xhs-q01"] and row["executable_query_ids"] == ["wechat-q01"]))

    plan = copy.deepcopy(valid)
    plan["acceptance_mode"] = "exempt_simple_direct_retrieval"
    plan["acceptance"]["exemption_reason"] = "精确记录读取"
    plan["acceptance"]["direct_retrieval_target"] = "一个指定记录"
    cases.append(case("simple_exemption_rejects_multi_query_research", plan, "fail", lambda row: bool(row["errors"])))

    plan = copy.deepcopy(valid)
    plan["queries"][0]["minimum_actual_opens"] = 0
    cases.append(case("per_query_actual_open_floor_required", plan, "fail", lambda row: bool(row["errors"])))

    report = {
        "schema": "social_query_plan_fixture_report.v1",
        "status": "pass" if all(row["passed"] for row in cases) else "fail",
        "case_count": len(cases),
        "failure_count": sum(not row["passed"] for row in cases),
        "cases": cases,
        "platform_opened": False,
        "network_accessed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
