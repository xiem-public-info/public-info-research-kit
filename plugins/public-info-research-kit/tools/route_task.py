#!/usr/bin/env python3
"""Build a deterministic, advisory-only public-information route plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "public_info_research_request.v1"
REQUIRED = (
    "task_id",
    "subject",
    "business_question",
    "requested_evidence",
    "channel_scope",
    "usage_boundary",
    "stop_condition",
)
CHANNELS = {
    "wechat",
    "xhs",
    "public_web",
    "public_dynamic_page",
    "official_document",
    "rss_feed",
    "map_gis",
}
SOCIAL_STRATEGY = "social_semantic_query_lexicon.v0.1"
CAPABILITY_PROFILES = {
    "wechat": "resources/channel-capability-profiles/wechat.v1.json",
    "wechat_ai_search": "resources/channel-capability-profiles/wechat-ai-search.v1.json",
    "xhs": "resources/channel-capability-profiles/xhs.v1.json",
    "public_web": "resources/channel-capability-profiles/public-web-official-feed.v1.json",
    "public_dynamic_page": "resources/channel-capability-profiles/public-web-official-feed.v1.json",
    "official_document": "resources/channel-capability-profiles/public-web-official-feed.v1.json",
    "rss_feed": "resources/channel-capability-profiles/public-web-official-feed.v1.json",
    "map_gis": "resources/channel-capability-profiles/osm-spatial.v1.json",
}


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def _route_wechat(request: dict[str, Any], errors: list[str]) -> list[dict[str, Any]]:
    cfg = request.get("wechat") or {}
    ai_queries = cfg.get("ai_queries") or []
    modes = [
        ("keyword_discovery", cfg.get("queries"), "skills/wechat-public-research", True),
        ("account_list_discovery", cfg.get("publisher_accounts"), "skills/wechat-public-research", True),
        ("known_url_browser_open", cfg.get("known_urls"), "skills/wechat-known-url-reader", False),
    ]
    selected = [(mode, value, skill, requires_gui) for mode, value, skill, requires_gui in modes if value]
    if not selected and not ai_queries:
        errors.append("wechat channel requires ai_queries, queries, publisher_accounts, or known_urls")
        return []
    routes = []
    if ai_queries:
        routes.append(
            {
                "channel": "wechat",
                "surface_id": "wechat_ai_search",
                "mode": "aggregate_ai_gate_preparation",
                "skill": "skills/wechat-public-research",
                "capability_profile": CAPABILITY_PROFILES["wechat_ai_search"],
                "input_count": len(ai_queries),
                "uses_declared_task_scope": True,
                "requires_shared_gui_serialization": False,
                "searcher_mode": request.get("searcher_mode") or "researcher",
                "query_strategy": SOCIAL_STRATEGY,
                "gate_request_schema": "wechat_ai_search_gate_request.v1",
                "gate_tool": "tools/check_wechat_ai_search_gate_preflight.py",
                "research_orchestration_schema": "d292_research_orchestration.v1",
                "research_orchestration_tool": "tools/validate_d292_research_orchestration.py",
                "status": "gate_ready_not_live_validated",
                "execution_authorized": False,
                "real_gui_validated": False,
                "original_source_backread_required": True,
                "default_executes_platform": False,
            }
        )
    for mode, value, skill, requires_gui in selected:
        route = {
            "channel": "wechat",
            "mode": mode,
            "skill": skill,
            "capability_profile": CAPABILITY_PROFILES["wechat"],
            "input_count": len(value),
            "uses_declared_task_scope": True,
            "requires_shared_gui_serialization": requires_gui,
            "searcher_mode": request.get("searcher_mode") or "researcher",
            "query_strategy": SOCIAL_STRATEGY,
            "query_plan_schema": "social_query_plan.v1",
            "default_executes_platform": False,
        }
        if requires_gui:
            route.update(
                {
                    "portable_preflight_schema": "portable_channel_request.v1",
                    "portable_preflight_tool": "tools/check_portable_channel_preflight.py",
                    "computer_use_installation_policy": "end_user_installs_and_authorizes_package_reminds_and_detects_only",
                }
            )
        routes.append(route)
    return routes


def build_plan(request: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if request.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    for field in REQUIRED:
        if not _nonempty(request.get(field)):
            errors.append(f"missing required field: {field}")

    channel_scope = request.get("channel_scope")
    if not isinstance(channel_scope, list) or not channel_scope:
        errors.append("channel_scope must be a non-empty list")
        channel_scope = []
    unknown = sorted(set(channel_scope) - CHANNELS)
    if unknown:
        errors.append("unsupported channels: " + ", ".join(unknown))

    routes: list[dict[str, Any]] = []
    for channel in channel_scope:
        if channel == "wechat":
            routes.extend(_route_wechat(request, errors))
        elif channel == "xhs":
            queries = (request.get("xhs") or {}).get("queries") or []
            if not queries:
                errors.append("xhs channel requires queries")
            else:
                routes.append({"channel": "xhs", "mode": "visible_search", "skill": "skills/xhs-visible-research", "capability_profile": CAPABILITY_PROFILES["xhs"], "input_count": len(queries), "uses_declared_task_scope": True, "requires_shared_gui_serialization": True, "searcher_mode": request.get("searcher_mode") or "researcher", "query_strategy": SOCIAL_STRATEGY, "query_plan_schema": "social_query_plan.v1", "portable_preflight_schema": "portable_channel_request.v1", "portable_preflight_tool": "tools/check_portable_channel_preflight.py", "computer_use_installation_policy": "end_user_installs_and_authorizes_package_reminds_and_detects_only", "default_executes_platform": False})
        elif channel in {"public_web", "official_document"}:
            cfg = request.get(channel) or request.get("public_web") or {}
            inputs = (cfg.get("known_urls") or []) + (cfg.get("queries") or [])
            if not inputs:
                errors.append(f"{channel} requires known_urls or queries")
            else:
                routes.append({"channel": channel, "mode": "official_source_resolution", "skill": "skills/public-web-official-resolver", "capability_profile": CAPABILITY_PROFILES[channel], "input_count": len(inputs), "uses_declared_task_scope": True, "requires_shared_gui_serialization": False, "default_executes_platform": False})
        elif channel == "public_dynamic_page":
            cfg = request.get("public_dynamic_page") or {}
            inputs = (cfg.get("known_urls") or []) + (cfg.get("queries") or [])
            if not inputs:
                errors.append("public_dynamic_page requires known_urls or queries")
            else:
                routes.append({"channel": channel, "mode": "public_dynamic_runtime_capture", "skill": "skills/public-web-official-resolver", "capability_profile": CAPABILITY_PROFILES[channel], "input_count": len(inputs), "uses_declared_task_scope": True, "requires_shared_gui_serialization": False, "default_executes_platform": False, "static_probe_first": True, "browser_runtime_only_if_needed": True})
        elif channel == "rss_feed":
            cfg = request.get("rss_feed") or {}
            feeds = cfg.get("feed_urls") or []
            if not feeds:
                errors.append("rss_feed requires feed_urls")
            else:
                routes.append({"channel": channel, "mode": "public_feed_discovery", "skill": "skills/public-web-official-resolver", "capability_profile": CAPABILITY_PROFILES[channel], "input_count": len(feeds), "uses_declared_task_scope": True, "requires_shared_gui_serialization": False, "default_executes_platform": False, "discovery_only": True, "original_source_resolution_required": True})
        elif channel == "map_gis":
            cfg = request.get("map_gis") or {}
            if not cfg.get("project_anchor"):
                errors.append("map_gis requires project_anchor")
            else:
                routes.append({"channel": "map_gis", "mode": "spatial_evidence", "skill": "skills/map-spatial-evidence", "capability_profile": CAPABILITY_PROFILES["map_gis"], "input_count": 1 + len(cfg.get("pois") or []), "uses_declared_task_scope": True, "requires_shared_gui_serialization": False, "default_executes_platform": False, "output_contract": "spatial_coordinate_evidence.v2", "validator": "tools/validate_spatial_coordinate_evidence_v2.py", "object_set_owner": "downstream_consumer", "project_location_model": "single_map_marker_centerpoint", "rendering_owner": "downstream_consumer", "display_validation_required_for_coordinate_package": False})

    canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "schema": "public_info_route_plan.v1",
        "status": "pass" if not errors else "fail",
        "request_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "task_id": request.get("task_id"),
        "routes": routes,
        "evidence_delivery_skill": "skills/public-evidence-delivery",
        "usage_boundary": request.get("usage_boundary"),
        "stop_condition": request.get("stop_condition"),
        "errors": errors,
        "advisory_only": True,
        "platform_opened": False,
        "network_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    result = build_plan(request)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
