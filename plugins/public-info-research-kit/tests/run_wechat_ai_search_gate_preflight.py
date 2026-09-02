#!/usr/bin/env python3
"""Offline positive and negative fixtures for the portable WeChat AI gate."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/check_wechat_ai_search_gate_preflight.py"
FIXTURES = ROOT / "tests/fixtures/wechat-ai-search-gate/cases.json"
SPEC = importlib.util.spec_from_file_location("wechat_ai_search_gate", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def run_case(case_id: str, request: dict, expected_status: str, expected_pass: bool, *, require_live: bool = False) -> dict:
    receipt = MODULE.validate(request, require_live=require_live)
    passed = (
        receipt["status"] == expected_status
        and receipt["passed"] is expected_pass
        and receipt["execution_authorized"] is False
        and receipt["real_gui_validated"] is False
        and receipt["platform_opened"] is False
        and receipt["network_accessed"] is False
        and receipt["external_action_executed"] is False
    )
    return {
        "case_id": case_id,
        "expected_status": expected_status,
        "actual_status": receipt["status"],
        "expected_pass": expected_pass,
        "actual_pass": receipt["passed"],
        "passed": passed,
    }


def main() -> int:
    fixture = json.loads(FIXTURES.read_text(encoding="utf-8"))
    valid = fixture["valid_request"]
    cases = [
        run_case("valid_owner_scoped_offline_gate", valid, "gate_ready_not_live_validated", True),
        run_case("require_live_is_rejected", valid, "wechat_ai_search_live_not_validated", False, require_live=True),
    ]
    for row in fixture["negative_cases"]:
        request = copy.deepcopy(valid)
        request.update(row["set"])
        cases.append(run_case(row["case_id"], request, row["expected_status"], False))
    report = {
        "schema": "wechat_ai_search_gate_fixture_report.v1",
        "status": "pass" if all(row["passed"] for row in cases) else "fail",
        "case_count": len(cases),
        "failure_count": sum(not row["passed"] for row in cases),
        "cases": cases,
        "offline_only": True,
        "real_gui_validated": False,
        "platform_opened": False,
        "network_accessed": False,
        "external_write_executed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
