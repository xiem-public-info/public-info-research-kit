#!/usr/bin/env python3
"""Offline XHS pointer and account-state security fixtures."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/validate_xhs_evidence_security.py"
SPEC = importlib.util.spec_from_file_location("validate_xhs_evidence_security", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def check(case_id: str, payload, expected: bool) -> dict:
    receipt = MODULE.validate(payload)
    return {
        "case_id": case_id,
        "expected_passed": expected,
        "actual_passed": receipt["passed"],
        "passed": receipt["passed"] is expected and receipt["values_exposed"] is False,
    }


def main() -> int:
    clean = {"stable_pointer": "https://www.xiaohongshu.com/explore/example", "visible_text": "公开可见内容"}
    cases = [
        check("clean_pointer", clean, True),
        check("xsec_field_rejected", {**clean, "xsec_token": "fixture"}, False),
        check("cookie_field_rejected", {**clean, "cookie": "fixture"}, False),
        check("xsec_query_rejected", {"stable_pointer": "https://www.xiaohongshu.com/explore/example?xsec_token=fixture"}, False),
        check("profile_path_rejected", {"pointer": "/Users/example/Library/Application Support/Google/Chrome/Default"}, False),
    ]
    dirty = {
        "stable_pointer": "https://www.xiaohongshu.com/explore/example?xsec_token=fixture&source=search",
        "cookie": "fixture",
        "nested": {"storage_state": {"fixture": True}},
    }
    sanitized = MODULE.sanitize(dirty)
    sanitized_receipt = MODULE.validate(sanitized)
    cases.append(
        {
            "case_id": "sanitizer_removes_account_state_and_transient_query",
            "expected_passed": True,
            "actual_passed": sanitized_receipt["passed"],
            "passed": sanitized_receipt["passed"] and "xsec_token" not in json.dumps(sanitized) and "cookie" not in sanitized,
        }
    )
    cases.append(
        {
            "case_id": "sanitizer_preserves_stable_source_path",
            "expected_passed": True,
            "actual_passed": sanitized_receipt["passed"],
            "passed": sanitized.get("stable_pointer") == "https://www.xiaohongshu.com/explore/example?source=search",
        }
    )
    report = {
        "schema": "xhs_evidence_security_fixture_report.v1",
        "status": "pass" if all(row["passed"] for row in cases) else "fail",
        "case_count": len(cases),
        "failure_count": sum(not row["passed"] for row in cases),
        "cases": cases,
        "values_exposed": False,
        "platform_opened": False,
        "external_write_executed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
