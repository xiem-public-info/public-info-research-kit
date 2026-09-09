#!/usr/bin/env python3
"""Validate the portable D-292 WeChat AI surface gate without opening WeChat."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from retrieval_task_policy import validate_task_authorization
from check_portable_channel_preflight import validate as validate_owner


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "resources/channel-capability-profiles/wechat-ai-search.v1.json"
ALLOWED_PURPOSES = {
    "semantic_clarification", "next_query_planning",
    "object_disambiguation",
    "content_supply_density_estimation",
    "original_source_navigation",
    "counterexample_and_lifecycle_clue_discovery",
}
ALLOWED_ORIGINAL_SURFACES = {
    "wechat_global_article_results",
    "public_account_article_list",
    "public_account_internal_search",
    "known_public_article_url",
}
ORDINARY_SURFACES = ALLOWED_ORIGINAL_SURFACES
REQUIRED_FIELDS = {
    "schema",
    "task_id",
    "channel",
    "platform",
    "aggregate_surface_id",
    "aggregate_surface_contract_version",
    "execution_owner",
    "downstream_business_owner",
    "business_question",
    "aggregate_purpose",
    "ordinary_original_source_surfaces",
    "aggregate_answer_evidence_allowed",
    "live_execution_requested",
    "real_gui_validated",
}
SENSITIVE_OR_CONTROL_FIELDS = {
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
    "profile_path",
    "coordinates",
    "fallback_route",
    "requested_executor",
}


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _collect_forbidden(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            business_authorization = (key == "authorization" and value.get("schema") == "residential.upstream_task.v0.2" and child in ("confirmed", "synthetic_fixture"))
            if not business_authorization and str(key).casefold() in SENSITIVE_OR_CONTROL_FIELDS:
                findings.append(child_path)
            findings.extend(_collect_forbidden(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_collect_forbidden(child, f"{path}[{index}]"))
    return findings


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _receipt(status: str, passed: bool, request: dict[str, Any], profile: dict[str, Any], **extra: object) -> dict[str, Any]:
    return {
        "schema": "wechat_ai_search_gate_receipt.v1",
        "status": status,
        "passed": passed,
        "task_id": request.get("task_id"),
        "channel": request.get("channel"),
        "platform": request.get("platform"),
        "aggregate_surface_id": request.get("aggregate_surface_id"),
        "contract_version": request.get("aggregate_surface_contract_version"),
        "execution_owner": request.get("execution_owner"),
        "downstream_business_owner": request.get("downstream_business_owner"),
        "execution_authorized": False,
        "real_gui_validated": False,
        "platform_opened": False,
        "network_accessed": False,
        "external_action_executed": False,
        "request_sha256": _canonical_sha256(request),
        "profile_sha256": _canonical_sha256(profile),
        **extra,
    }


def validate(request: dict[str, Any], *, require_live: bool = False) -> dict[str, Any]:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    forbidden = sorted(set(_collect_forbidden(request)))
    if forbidden:
        return _receipt("forbidden_control_or_sensitive_field", False, request, profile, forbidden_paths=forbidden)

    missing = sorted(field for field in REQUIRED_FIELDS if field not in request or request.get(field) in (None, ""))
    if missing:
        return _receipt("invalid_request", False, request, profile, missing_fields=missing)
    unknown = sorted(set(request) - REQUIRED_FIELDS - {"owner_request"})
    if unknown:
        return _receipt("invalid_request", False, request, profile, unknown_fields=unknown)
    if request.get("schema") != "wechat_ai_search_gate_request.v1":
        return _receipt("invalid_request", False, request, profile)
    if request.get("execution_owner") != "installed_public_info_research_kit" or not _nonempty(request.get("downstream_business_owner")):
        return _receipt("owner_preflight_not_ready", False, request, profile)
    if not _nonempty(request.get("business_question")):
        return _receipt("invalid_request", False, request, profile)
    if request.get("channel") != "wechat" or request.get("platform") != "wechat":
        return _receipt("aggregate_surface_identity_mismatch", False, request, profile)

    surface = request.get("aggregate_surface_id")
    if surface == "xhs_ask_diandian":
        return _receipt("cross_platform_aggregate_surface_forbidden", False, request, profile)
    if surface in ORDINARY_SURFACES:
        return _receipt("ordinary_search_masquerade_forbidden", False, request, profile)
    if surface != "wechat_ai_search" or request.get("aggregate_surface_contract_version") != "WECHAT-AI-SEARCH-SURFACE-V1":
        return _receipt("aggregate_surface_identity_mismatch", False, request, profile)
    if request.get("aggregate_purpose") not in ALLOWED_PURPOSES:
        return _receipt("aggregate_purpose_not_allowed", False, request, profile)
    if request.get("aggregate_answer_evidence_allowed") is not False:
        return _receipt("aggregate_answer_evidence_forbidden", False, request, profile)

    original_surfaces = request.get("ordinary_original_source_surfaces")
    if (
        not isinstance(original_surfaces, list)
        or not original_surfaces
        or any(surface not in ALLOWED_ORIGINAL_SURFACES for surface in original_surfaces)
    ):
        return _receipt("original_source_surface_required", False, request, profile)
    if request.get("real_gui_validated") is not False:
        return _receipt("preflight_cannot_claim_gui_validation", False, request, profile)
    if not isinstance(request.get("live_execution_requested"), bool):
        return _receipt("invalid_request", False, request, profile)
    if require_live or request.get("live_execution_requested") or "owner_request" in request:
        owner_request = request.get("owner_request")
        if not isinstance(owner_request, dict):
            return _receipt("retrieval_task_contract_required", False, request, profile)
        valid, status = validate_task_authorization(owner_request)
        if not valid:
            return _receipt(status, False, request, profile)
        if any(owner_request.get(key) != request.get(key) for key in ("task_id", "channel", "business_question", "downstream_business_owner")) or owner_request.get("surface_id") != "wechat_ai_search":
            return _receipt("owner_request_scope_mismatch", False, request, profile)
        if any(q.get("surface_id") != "wechat_ai_search" for q in owner_request.get("query_plan", [])):
            return _receipt("owner_request_scope_mismatch", False, request, profile)
        owner = validate_owner(owner_request, require_live=bool(require_live or request.get("live_execution_requested")))
        if not owner["passed"]:
            return _receipt("owner_preflight_not_ready", False, request, profile, owner_receipt=owner)
        return _receipt("task_authorized_not_executed", True, request, profile,
            execution_authorized=owner["execution_authorized"], owner_receipt=owner,
            aggregate_output_role="ai_aggregate_clue", original_source_backread_required=True)

    return _receipt(
        "gate_ready_not_live_validated",
        True,
        request,
        profile,
        aggregate_output_role="ai_aggregate_clue",
        original_source_backread_required=True,
        status_ceiling="gate_ready_not_live_validated",
    )


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
