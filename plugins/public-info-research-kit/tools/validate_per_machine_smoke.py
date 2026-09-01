#!/usr/bin/env python3
"""Validate one machine/channel smoke receipt without opening any platform."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "per_machine_smoke_receipt.v1"
CHANNELS = {"non_gui_public_web", "wechat", "xhs"}
TOP_FIELDS = {"schema", "receipt_id", "package_version", "channel", "operator_scope", "installation", "doctor", "prerequisites", "observations", "result", "boundary"}
VISIBLE_CONTENT_TYPES = {"title", "body", "subtitle", "image_text", "visible_comment"}
FORBIDDEN_KEYS = {"cookie", "cookies", "authorization", "token", "accesstoken", "refreshtoken", "storagestate", "localstorage", "sessionstorage", "profilepath", "browserprofile", "userdatadir", "accountname", "querytext", "exactquerytext", "screenshot", "clipboardcontent"}


def norm_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def nonnegative_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def walk(value: Any, path: str = "$") -> Iterable[tuple[str, Any, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            yield child_path, child, str(key)
            yield from walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            yield child_path, child, ""
            yield from walk(child, child_path)


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    unknown = sorted(set(payload) - TOP_FIELDS)
    if unknown:
        errors.append("unknown top-level fields: " + ", ".join(unknown))
    for field in ("receipt_id", "package_version", "boundary"):
        if not nonempty(payload.get(field)):
            errors.append(f"{field} is required")
    channel = payload.get("channel")
    if channel not in CHANNELS:
        errors.append("channel is invalid")
    if payload.get("operator_scope") != "end_user_on_own_machine":
        errors.append("operator_scope must be end_user_on_own_machine")

    installation = payload.get("installation")
    if not isinstance(installation, dict):
        errors.append("installation must be an object")
        installation = {}
    elif set(installation) - {"plugin_visible", "skill_count"}:
        errors.append("installation has unknown fields")
    if installation.get("plugin_visible") not in {True, False}:
        errors.append("installation.plugin_visible must be boolean")
    if not nonnegative_integer(installation.get("skill_count")):
        errors.append("installation.skill_count must be a non-negative integer")

    doctor = payload.get("doctor")
    if not isinstance(doctor, dict):
        errors.append("doctor must be an object")
        doctor = {}
    elif set(doctor) - {"executed", "status", "network_probe", "writes_performed"}:
        errors.append("doctor has unknown fields")
    if doctor.get("executed") not in {True, False}:
        errors.append("doctor.executed must be boolean")
    if doctor.get("status") not in {"pass", "gaps_detected", "not_run"}:
        errors.append("doctor.status is invalid")
    if doctor.get("network_probe") not in {"none", "tls_only"}:
        errors.append("doctor.network_probe is invalid")
    if doctor.get("writes_performed") is not False:
        errors.append("doctor must remain read-only")

    prerequisites = payload.get("prerequisites")
    if not isinstance(prerequisites, dict):
        errors.append("prerequisites must be an object")
        prerequisites = {}
    elif set(prerequisites) - {"computer_use_state", "login_state", "live_task_authorized", "shared_gui_serialized"}:
        errors.append("prerequisites has unknown fields")
    if prerequisites.get("computer_use_state") not in {"not_required", "end_user_confirmed_ready", "missing", "unknown"}:
        errors.append("prerequisites.computer_use_state is invalid")
    if prerequisites.get("login_state") not in {"not_required", "end_user_confirmed_own_wechat", "end_user_confirmed_own_xhs_in_normal_chrome", "not_ready"}:
        errors.append("prerequisites.login_state is invalid")
    for field in ("live_task_authorized", "shared_gui_serialized"):
        if prerequisites.get(field) not in {True, False}:
            errors.append(f"prerequisites.{field} must be boolean")

    observations = payload.get("observations")
    if not isinstance(observations, dict):
        errors.append("observations must be an object")
        observations = {}
    else:
        allowed = {"exact_query_submitted_count", "exact_query_visible_before_submit", "opened_content_count", "content_progress_count", "stable_source_pointer_count", "visible_content_types", "external_interaction_or_publish_executed", "account_state_persisted", "safe_exit_observed", "stop_reason"}
        if set(observations) - allowed:
            errors.append("observations has unknown fields")
    for field in ("exact_query_submitted_count", "opened_content_count", "content_progress_count", "stable_source_pointer_count"):
        if not nonnegative_integer(observations.get(field)):
            errors.append(f"observations.{field} must be a non-negative integer")
    for field in ("exact_query_visible_before_submit", "external_interaction_or_publish_executed", "account_state_persisted", "safe_exit_observed"):
        if observations.get(field) not in {True, False}:
            errors.append(f"observations.{field} must be boolean")
    visible_types = observations.get("visible_content_types")
    if not isinstance(visible_types, list) or not all(item in VISIBLE_CONTENT_TYPES for item in visible_types):
        errors.append("observations.visible_content_types is invalid")
    if not nonempty(observations.get("stop_reason")):
        errors.append("observations.stop_reason is required")

    result = payload.get("result")
    if not isinstance(result, dict):
        errors.append("result must be an object")
        result = {}
    elif set(result) - {"state", "business_acceptance"}:
        errors.append("result has unknown fields")
    if result.get("state") not in {"passed", "failed", "not_run"}:
        errors.append("result.state is invalid")
    if result.get("business_acceptance") != "not_assessed":
        errors.append("smoke cannot claim business acceptance")

    for path, value, key in walk(payload):
        if key and norm_key(key) in FORBIDDEN_KEYS:
            errors.append(f"forbidden sensitive or unnecessary field at {path}")
        if isinstance(value, str) and ("/Users/" in value or "file:///" in value):
            errors.append(f"local path is forbidden at {path}")

    if result.get("state") == "passed":
        if installation.get("plugin_visible") is not True or installation.get("skill_count") != 7:
            errors.append("passed smoke requires installed_visible with seven skills")
        if doctor.get("executed") is not True or doctor.get("status") != "pass":
            errors.append("passed smoke requires doctor pass")
        if prerequisites.get("live_task_authorized") is not True:
            errors.append("passed smoke requires live task authorization")
        if observations.get("external_interaction_or_publish_executed") is not False:
            errors.append("smoke must not interact or publish")
        if observations.get("account_state_persisted") is not False:
            errors.append("smoke must not persist account state")
        if channel == "non_gui_public_web":
            if prerequisites.get("computer_use_state") != "not_required" or prerequisites.get("login_state") != "not_required":
                errors.append("non-GUI smoke must not require Computer Use or login")
            if prerequisites.get("shared_gui_serialized") is not False:
                errors.append("non-GUI smoke must not claim shared GUI use")
            if observations.get("opened_content_count", 0) < 1 or observations.get("stable_source_pointer_count", 0) < 1:
                errors.append("non-GUI smoke requires one opened source and stable pointer")
        elif channel == "wechat":
            if prerequisites.get("computer_use_state") != "end_user_confirmed_ready" or prerequisites.get("login_state") != "end_user_confirmed_own_wechat":
                errors.append("WeChat smoke prerequisites are not confirmed by the end user")
            if prerequisites.get("shared_gui_serialized") is not True:
                errors.append("WeChat smoke requires shared GUI serialization")
            if observations.get("exact_query_submitted_count") != 1 or observations.get("exact_query_visible_before_submit") is not True:
                errors.append("WeChat smoke requires one visibly confirmed query submission")
            if observations.get("opened_content_count", 0) < 1 or observations.get("content_progress_count", 0) < 2 or "body" not in (visible_types or []):
                errors.append("WeChat smoke requires one opened article and two body progress actions")
            if observations.get("safe_exit_observed") is not True:
                errors.append("WeChat smoke requires safe exit")
        elif channel == "xhs":
            if prerequisites.get("computer_use_state") != "end_user_confirmed_ready" or prerequisites.get("login_state") != "end_user_confirmed_own_xhs_in_normal_chrome":
                errors.append("XHS smoke prerequisites are not confirmed by the end user")
            if prerequisites.get("shared_gui_serialized") is not True:
                errors.append("XHS smoke requires shared GUI serialization")
            if observations.get("exact_query_submitted_count") != 1 or observations.get("exact_query_visible_before_submit") is not True:
                errors.append("XHS smoke requires one visibly confirmed query submission")
            content_types = set(visible_types or []) & {"body", "subtitle", "image_text", "visible_comment"}
            if observations.get("opened_content_count", 0) < 1 or observations.get("stable_source_pointer_count", 0) < 1 or not content_types:
                errors.append("XHS smoke requires one opened note, stable pointer and visible content")
            if observations.get("safe_exit_observed") is not True:
                errors.append("XHS smoke requires safe exit")

    errors = sorted(set(errors))
    return {
        "schema": "per_machine_smoke_validation.v1",
        "status": "pass" if not errors else "fail",
        "passed": not errors,
        "channel": channel,
        "claimed_smoke_state": result.get("state"),
        "business_acceptance": result.get("business_acceptance"),
        "errors": errors,
        "platform_opened": False,
        "external_write_executed": False,
        "validation_only": True
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    receipt = validate(json.loads(args.input.read_text(encoding="utf-8")))
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
