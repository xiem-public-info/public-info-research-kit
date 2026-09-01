#!/usr/bin/env python3
"""Offline positive and negative fixtures for per-machine smoke receipts."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/validate_per_machine_smoke.py"
SPEC = importlib.util.spec_from_file_location("validate_per_machine_smoke", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def base(channel: str) -> dict:
    prerequisites = {
        "computer_use_state": "not_required",
        "login_state": "not_required",
        "live_task_authorized": True,
        "shared_gui_serialized": False,
    }
    observations = {
        "exact_query_submitted_count": 0,
        "exact_query_visible_before_submit": False,
        "opened_content_count": 1,
        "content_progress_count": 1,
        "stable_source_pointer_count": 1,
        "visible_content_types": ["body"],
        "external_interaction_or_publish_executed": False,
        "account_state_persisted": False,
        "safe_exit_observed": True,
        "stop_reason": "完成该渠道最小 smoke 条件",
    }
    if channel == "wechat":
        prerequisites.update({"computer_use_state": "end_user_confirmed_ready", "login_state": "end_user_confirmed_own_wechat", "shared_gui_serialized": True})
        observations.update({"exact_query_submitted_count": 1, "exact_query_visible_before_submit": True, "content_progress_count": 2})
    elif channel == "xhs":
        prerequisites.update({"computer_use_state": "end_user_confirmed_ready", "login_state": "end_user_confirmed_own_xhs_in_normal_chrome", "shared_gui_serialized": True})
        observations.update({"exact_query_submitted_count": 1, "exact_query_visible_before_submit": True, "visible_content_types": ["image_text"]})
    return {
        "schema": "per_machine_smoke_receipt.v1",
        "receipt_id": f"SMOKE-{channel}",
        "package_version": "0.8.0-rc.1",
        "channel": channel,
        "operator_scope": "end_user_on_own_machine",
        "installation": {"plugin_visible": True, "skill_count": 7},
        "doctor": {"executed": True, "status": "pass", "network_probe": "none", "writes_performed": False},
        "prerequisites": prerequisites,
        "observations": observations,
        "result": {"state": "passed", "business_acceptance": "not_assessed"},
        "boundary": "只证明这一台电脑、这一渠道、这一次 smoke；不证明业务接受",
    }


def check(case_id: str, payload: dict, expected: bool, error_contains: str | None = None) -> dict:
    receipt = MODULE.validate(payload)
    matched = True if error_contains is None else any(error_contains in error for error in receipt["errors"])
    return {"case_id": case_id, "expected_passed": expected, "actual_passed": receipt["passed"], "passed": receipt["passed"] is expected and matched}


def main() -> int:
    cases = [
        check("non_gui_smoke_passes_without_computer_use", base("non_gui_public_web"), True),
        check("wechat_minimum_real_smoke_contract", base("wechat"), True),
        check("xhs_minimum_real_smoke_contract", base("xhs"), True),
    ]
    row = base("wechat")
    row["installation"]["plugin_visible"] = False
    cases.append(check("hidden_plugin_cannot_pass", row, False, "installed_visible"))
    row = base("wechat")
    row["installation"]["skill_count"] = 6
    cases.append(check("six_skills_cannot_pass", row, False, "seven skills"))
    row = base("wechat")
    row["doctor"].update({"executed": False, "status": "not_run"})
    cases.append(check("doctor_not_run_cannot_pass", row, False, "doctor pass"))
    row = base("wechat")
    row["prerequisites"]["computer_use_state"] = "missing"
    cases.append(check("wechat_missing_computer_use_cannot_pass", row, False, "prerequisites"))
    row = base("wechat")
    row["observations"]["exact_query_submitted_count"] = 2
    cases.append(check("wechat_repeated_submission_cannot_pass", row, False, "one visibly confirmed"))
    row = base("xhs")
    row["observations"]["external_interaction_or_publish_executed"] = True
    cases.append(check("xhs_interaction_cannot_pass", row, False, "must not interact"))
    row = base("xhs")
    row["result"]["business_acceptance"] = "accepted"
    cases.append(check("smoke_cannot_claim_business_acceptance", row, False, "cannot claim business acceptance"))
    row = base("xhs")
    row["observations"]["account_state_persisted"] = True
    cases.append(check("account_state_persistence_cannot_pass", row, False, "must not persist"))

    report = {
        "schema": "per_machine_smoke_contract_fixture_report.v1",
        "status": "pass" if all(row["passed"] for row in cases) else "fail",
        "case_count": len(cases),
        "failure_count": sum(not row["passed"] for row in cases),
        "cases": cases,
        "network_accessed": False,
        "platform_opened": False,
        "external_write_executed": False,
        "real_smoke_executed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
