#!/usr/bin/env python3
"""Offline policy fixtures for doctor and end-user-owned GUI prerequisites."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/doctor.py"
SPEC = importlib.util.spec_from_file_location("doctor", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def main() -> int:
    enabled = [{"pluginId": "computer-use@openai-bundled", "name": "computer-use", "installed": True, "enabled": True, "version": "fixture"}]
    disabled = [{"pluginId": "computer-use@openai-bundled", "name": "computer-use", "installed": True, "enabled": False, "version": "fixture"}]
    cases = []

    row = MODULE.computer_use_finding(enabled)
    cases.append({"case_id": "enabled_computer_use_detected", "passed": row["status"] == "pass" and row["observed"]["enabled"] is True})
    row = MODULE.computer_use_finding(disabled)
    cases.append({"case_id": "disabled_computer_use_requires_end_user_action", "passed": row["status"] == "gap" and "终端用户" in row["action"] and "自行启用" in row["action"]})
    row = MODULE.computer_use_finding([])
    cases.append({"case_id": "missing_computer_use_requires_end_user_action", "passed": row["status"] == "gap" and "自行安装" in row["action"]})

    prerequisites = {item["name"]: item for item in MODULE.manual_prerequisite_findings({"wechat", "xhs"})}
    cases.append({"case_id": "permissions_are_reminder_not_automatic_action", "passed": prerequisites["computer_use_macos_permissions"]["status"] == "notice" and prerequisites["computer_use_macos_permissions"]["observed"] == "not_verified_by_doctor"})
    cases.append({"case_id": "wechat_login_is_end_user_owned", "passed": "登录自己的微信" in prerequisites["wechat_end_user_session"]["action"]})
    cases.append({"case_id": "xhs_login_is_end_user_owned", "passed": "自己的正常可见 Chrome" in prerequisites["xhs_end_user_session"]["action"]})
    cases.append({"case_id": "offline_is_the_default", "passed": MODULE.network_finding(False)["status"] == "not_checked"})

    source = MODULE_PATH.read_text(encoding="utf-8")
    forbidden_actions = ("plugin add computer-use", "plugin enable computer-use", "tccutil reset", "osascript")
    cases.append({"case_id": "doctor_contains_no_install_enable_or_permission_command", "passed": not any(token in source for token in forbidden_actions)})

    report = {
        "schema": "doctor_policy_fixture_report.v1",
        "status": "pass" if all(row["passed"] for row in cases) else "fail",
        "case_count": len(cases),
        "failure_count": sum(not row["passed"] for row in cases),
        "cases": cases,
        "network_accessed": False,
        "platform_opened": False,
        "external_write_executed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
