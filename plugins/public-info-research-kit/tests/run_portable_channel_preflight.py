#!/usr/bin/env python3
"""Offline positive and negative cases for portable channel preflight."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/check_portable_channel_preflight.py"
SPEC = importlib.util.spec_from_file_location("portable_channel_preflight", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def base_request(channel: str = "wechat") -> dict:
    request = {
        "schema": "portable_channel_request.v1",
        "task_id": f"fixture-{channel}",
        "channel": channel,
        "channel_profile": f"{channel}.v1",
        "execution_owner": "installed_public_info_research_kit",
        "downstream_business_owner": "fixture_consumer",
        "business_question": "哪些公开证据能支持或反驳当前业务判断",
        "intent": "研究检索",
        "evidence_type": "public_evidence",
        "usage_boundary": "内部研究候选，不直接升级为项目硬事实",
        "stop_condition": "完成约定覆盖或触发登录、安全、不可读停止线",
        "query_plan_schema": "social_query_plan.v1",
        "query_plan": [
            {
                "query_id": f"{channel}-q01",
                "platform": channel,
                "exact_query_text": "某城市 某项目 交付后 使用体验",
                "execution_state": "frozen",
                "acceptance": {"minimum_result_batches": 2, "minimum_actual_opens": 2},
            }
        ],
        "shared_gui": {
            "resource_id": "high_state_ui",
            "serialization_required": True,
            "lease_state": "acquired",
        },
        "computer_use": {
            "installation_owner": "end_user",
            "package_action": "remind_and_detect_only",
            "available": True,
            "permissions_ready": True,
        },
        "end_user_session": {
            "login_owner": "end_user",
            "logged_in": True,
            "surface": "wechat_public_search_preopened" if channel == "wechat" else "existing_normal_visible_chrome",
        },
        "live_gate": {
            "authorized": True,
            "approved_by": "end_user",
            "read_only": True,
            "stop_condition": "登录、验证码、风控或页面不可读即停止",
        },
        "adaptive_extension_authorized": False,
    }

    from compile_retrieval_execution_request import compile_request
    consumer = json.loads((ROOT / "tests/fixtures/golden-tasks/golden_research_partial.json").read_text())["consumer_contract"]
    task = {"task_id": request["task_id"], "business_question": request["business_question"],
            "business_owner": "fixture_consumer", "subjects": ["Example project"],
            "stop_condition": request["stop_condition"], "sufficiency": consumer}
    plan = {key: copy.deepcopy(request[key]) for key in ("channel", "shared_gui", "computer_use", "end_user_session")}
    plan["queries"] = copy.deepcopy(request["query_plan"])
    return {**request, **compile_request(task, plan)}


def run_case(case_id: str, request: dict, expected_pass: bool, expected_status: str) -> dict:
    receipt = MODULE.validate(request, require_live=True)
    return {
        "case_id": case_id,
        "expected_pass": expected_pass,
        "actual_pass": receipt["passed"],
        "expected_status": expected_status,
        "actual_status": receipt["status"],
        "passed": receipt["passed"] is expected_pass and receipt["status"] == expected_status,
    }


def main() -> int:
    cases: list[dict] = []
    cases.append(run_case("valid_wechat", base_request("wechat"), True, "pass"))
    cases.append(run_case("valid_xhs", base_request("xhs"), True, "pass"))
    original_profile = MODULE.PROFILE_PATHS['xhs']
    with tempfile.TemporaryDirectory() as directory:
        try:
            for entry in ('cua.getTab', 'cua.getBrowser', 'cua.createBrowserTab'):
                profile = json.loads(original_profile.read_text())
                profile['execution_entrypoint'] = entry
                path = Path(directory) / 'xhs.json'
                path.write_text(json.dumps(profile))
                MODULE.PROFILE_PATHS['xhs'] = path
                cases.append(run_case('browser_entry_rejected:'+entry, base_request('xhs'), False, 'invalid_request'))
        finally:
            MODULE.PROFILE_PATHS['xhs'] = original_profile

    request = base_request()
    request["computer_use"]["available"] = False
    cases.append(run_case("computer_use_missing_is_end_user_action", request, False, "computer_use_installation_or_permissions_required"))

    request = base_request()
    request["requested_executor"] = "downstream_tool"
    cases.append(run_case("downstream_cannot_choose_executor", request, False, "invalid_request"))

    request = base_request()
    request["cookies"] = "forbidden"
    cases.append(run_case("account_state_is_rejected", request, False, "invalid_request"))

    request = base_request()
    request["query_plan"][0]["execution_state"] = "proposed_incremental"
    cases.append(run_case("incremental_proposal_not_live_executable", request, False, "invalid_request"))

    request = base_request("xhs")
    request["end_user_session"]["surface"] = "wechat_public_search_preopened"
    cases.append(run_case("cross_channel_surface_rejected", request, False, "end_user_session_not_ready"))

    request = base_request()
    request["shared_gui"]["lease_state"] = "planned"
    cases.append(run_case("live_gui_lease_required", request, False, "live_execution_gate_not_ready"))

    report = {
        "schema": "portable_channel_preflight_fixture_report.v1",
        "status": "pass" if all(case["passed"] for case in cases) else "fail",
        "case_count": len(cases),
        "failure_count": sum(not case["passed"] for case in cases),
        "cases": cases,
        "platform_opened": False,
        "external_write_executed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
