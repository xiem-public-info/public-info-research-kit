#!/usr/bin/env python3
"""Validate portable WeChat/XHS ownership and readiness without opening a platform."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATHS = {
    "wechat": ROOT / "resources/channel-capability-profiles/wechat.v1.json",
    "xhs": ROOT / "resources/channel-capability-profiles/xhs.v1.json",
}
EXPECTED_PROFILES = {"wechat": "wechat.v1", "xhs": "xhs.v1"}
ALLOWED_TOP_LEVEL = {
    "schema",
    "task_id",
    "channel",
    "channel_profile",
    "execution_owner",
    "downstream_business_owner",
    "business_question",
    "intent",
    "evidence_type",
    "usage_boundary",
    "stop_condition",
    "query_plan_schema",
    "query_plan",
    "shared_gui",
    "computer_use",
    "end_user_session",
    "live_gate",
    "adaptive_extension_authorized",
}
FORBIDDEN_CONTROL_FIELDS = {
    "requested_executor",
    "execution_surface",
    "session_surface",
    "fallback_route",
    "coordinates",
    "profile_path",
    "direct_channel_control_allowed",
}
FORBIDDEN_SENSITIVE_FIELDS = {
    "cookie",
    "cookies",
    "authorization",
    "token",
    "access_token",
    "refresh_token",
    "storage_state",
    "local_storage",
    "session_storage",
    "password",
}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _collect_forbidden(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            child_path = f"{path}.{key}"
            if lowered in FORBIDDEN_CONTROL_FIELDS or lowered in FORBIDDEN_SENSITIVE_FIELDS:
                findings.append(child_path)
            findings.extend(_collect_forbidden(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_collect_forbidden(child, f"{path}[{index}]"))
    return findings


def _validate_queries(request: dict[str, Any], channel: str, require_live: bool) -> list[str]:
    errors: list[str] = []
    rows = request.get("query_plan")
    if not isinstance(rows, list) or not rows:
        return ["query_plan_required"]
    seen: set[str] = set()
    for index, row in enumerate(rows):
        prefix = f"query_plan[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix}_must_be_object")
            continue
        allowed = {"query_id", "platform", "exact_query_text", "execution_state", "acceptance"}
        unknown = sorted(set(row) - allowed)
        if unknown:
            errors.append(f"{prefix}_unknown_fields:{','.join(unknown)}")
        query_id = row.get("query_id")
        if not _nonempty(query_id):
            errors.append(f"{prefix}_query_id_required")
        elif query_id in seen:
            errors.append(f"{prefix}_query_id_duplicate")
        else:
            seen.add(query_id)
        if row.get("platform") != channel:
            errors.append(f"{prefix}_platform_mismatch")
        if not _nonempty(row.get("exact_query_text")):
            errors.append(f"{prefix}_exact_query_text_required")
        state = row.get("execution_state")
        if state not in {"frozen", "proposed_incremental"}:
            errors.append(f"{prefix}_execution_state_invalid")
        elif require_live and state != "frozen":
            errors.append(f"{prefix}_proposed_incremental_not_live_executable")
        acceptance = row.get("acceptance")
        if not isinstance(acceptance, dict):
            errors.append(f"{prefix}_acceptance_required")
        else:
            if set(acceptance) - {"minimum_result_batches", "minimum_actual_opens"}:
                errors.append(f"{prefix}_acceptance_unknown_fields")
            for field in ("minimum_result_batches", "minimum_actual_opens"):
                value = acceptance.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                    errors.append(f"{prefix}_{field}_positive_integer_required")
    return errors


def validate(request: dict[str, Any], *, require_live: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if request.get("schema") != "portable_channel_request.v1":
        errors.append("schema_invalid")
    unknown = sorted(set(request) - ALLOWED_TOP_LEVEL)
    if unknown:
        errors.append("unknown_top_level_fields:" + ",".join(unknown))
    forbidden_paths = sorted(set(_collect_forbidden(request)))
    if forbidden_paths:
        errors.append("forbidden_control_or_sensitive_fields")

    for field in (
        "task_id",
        "downstream_business_owner",
        "business_question",
        "intent",
        "evidence_type",
        "usage_boundary",
        "stop_condition",
    ):
        if not _nonempty(request.get(field)):
            errors.append(f"{field}_required")

    channel = request.get("channel")
    if channel not in PROFILE_PATHS:
        errors.append("unsupported_channel")
        profile: dict[str, Any] = {}
    else:
        profile = json.loads(PROFILE_PATHS[channel].read_text(encoding="utf-8"))
        if request.get("channel_profile") != EXPECTED_PROFILES[channel]:
            errors.append("channel_profile_mismatch")
        if profile.get("execution_owner") != "installed_public_info_research_kit":
            errors.append("profile_execution_owner_invalid")

    if request.get("execution_owner") != "installed_public_info_research_kit":
        errors.append("execution_owner_invalid")
    if request.get("query_plan_schema") != "social_query_plan.v1":
        errors.append("query_plan_schema_invalid")
    if channel in PROFILE_PATHS:
        errors.extend(_validate_queries(request, channel, require_live))

    shared_gui = request.get("shared_gui")
    if not isinstance(shared_gui, dict):
        errors.append("shared_gui_required")
    else:
        if set(shared_gui) - {"resource_id", "serialization_required", "lease_state"}:
            errors.append("shared_gui_unknown_fields")
        if shared_gui.get("resource_id") != "high_state_ui" or shared_gui.get("serialization_required") is not True:
            errors.append("shared_gui_serialization_required")
        if shared_gui.get("lease_state") not in {"planned", "acquired"}:
            errors.append("shared_gui_lease_state_invalid")
        elif require_live and shared_gui.get("lease_state") != "acquired":
            errors.append("shared_gui_lease_not_acquired")

    computer_use = request.get("computer_use")
    if not isinstance(computer_use, dict):
        errors.append("computer_use_readiness_required")
    else:
        if set(computer_use) - {"installation_owner", "package_action", "available", "permissions_ready"}:
            errors.append("computer_use_unknown_fields")
        if computer_use.get("installation_owner") != "end_user":
            errors.append("computer_use_installation_owner_must_be_end_user")
        if computer_use.get("package_action") != "remind_and_detect_only":
            errors.append("computer_use_package_action_must_be_remind_and_detect_only")
        if computer_use.get("available") is not True or computer_use.get("permissions_ready") is not True:
            errors.append("computer_use_not_ready")

    session = request.get("end_user_session")
    if not isinstance(session, dict):
        errors.append("end_user_session_required")
    else:
        if set(session) - {"login_owner", "logged_in", "surface"}:
            errors.append("end_user_session_unknown_fields")
        if session.get("login_owner") != "end_user":
            errors.append("login_owner_must_be_end_user")
        if session.get("logged_in") is not True:
            errors.append("end_user_login_required")
        expected_surface = {
            "wechat": "wechat_public_search_preopened",
            "xhs": "existing_normal_visible_chrome",
        }.get(channel)
        if expected_surface and session.get("surface") != expected_surface:
            errors.append("channel_surface_not_ready")

    live_gate = request.get("live_gate")
    if not isinstance(live_gate, dict):
        errors.append("live_gate_required")
    else:
        if set(live_gate) - {"authorized", "approved_by", "read_only", "stop_condition"}:
            errors.append("live_gate_unknown_fields")
        if live_gate.get("approved_by") != "end_user" or live_gate.get("read_only") is not True:
            errors.append("live_gate_scope_invalid")
        if not _nonempty(live_gate.get("stop_condition")):
            errors.append("live_gate_stop_condition_required")
        if require_live and live_gate.get("authorized") is not True:
            errors.append("live_gate_not_authorized")
        elif not require_live and live_gate.get("authorized") is not True:
            warnings.append("dry_preflight_only_live_gate_not_authorized")

    if request.get("adaptive_extension_authorized") is not True:
        warnings.append("adaptive_extension_not_authorized_no_incremental_execution")

    if "computer_use_not_ready" in errors:
        status = "computer_use_installation_or_permissions_required"
    elif "end_user_login_required" in errors or "channel_surface_not_ready" in errors:
        status = "end_user_session_not_ready"
    elif any(error in errors for error in ("shared_gui_lease_not_acquired", "live_gate_not_authorized")):
        status = "live_execution_gate_not_ready"
    else:
        status = "pass" if not errors else "invalid_request"

    return {
        "schema": "portable_channel_preflight_receipt.v1",
        "status": status,
        "passed": not errors,
        "task_id": request.get("task_id"),
        "channel": channel,
        "channel_profile": request.get("channel_profile"),
        "execution_owner": request.get("execution_owner"),
        "downstream_business_owner": request.get("downstream_business_owner"),
        "query_count": len(request.get("query_plan") or []) if isinstance(request.get("query_plan"), list) else 0,
        "errors": errors,
        "warnings": warnings,
        "forbidden_paths": forbidden_paths,
        "request_sha256": _canonical_sha256(request),
        "profile_sha256": _canonical_sha256(profile) if profile else None,
        "require_live": require_live,
        "execution_authorized": require_live and not errors,
        "computer_use_action": "end_user_installs_and_authorizes_independently_package_only_reminds_and_detects",
        "automatic_computer_use_install_enable_or_permission_action": False,
        "platform_opened": False,
        "external_write_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--require-live", action="store_true")
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    receipt = validate(request, require_live=args.require_live)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
