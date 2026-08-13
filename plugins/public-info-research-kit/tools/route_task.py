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
CHANNELS = {"wechat", "xhs", "public_web", "official_document", "map_gis"}
SOCIAL_STRATEGY = "social_semantic_query_lexicon.v0.1"


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def _route_wechat(request: dict[str, Any], errors: list[str]) -> list[dict[str, Any]]:
    cfg = request.get("wechat") or {}
    modes = [
        ("keyword_discovery", cfg.get("queries"), "skills/wechat-public-research"),
        ("account_list_discovery", cfg.get("publisher_accounts"), "skills/wechat-public-research"),
        ("known_url_browser_open", cfg.get("known_urls"), "skills/wechat-known-url-reader"),
    ]
    selected = [(mode, value, skill) for mode, value, skill in modes if value]
    if not selected:
        errors.append("wechat channel requires queries, publisher_accounts, or known_urls")
        return []
    routes = []
    for mode, value, skill in selected:
        routes.append(
            {
                "channel": "wechat",
                "mode": mode,
                "skill": skill,
                "input_count": len(value),
                "uses_declared_task_scope": True,
                "requires_shared_gui_serialization": True,
                "searcher_mode": request.get("searcher_mode") or "researcher",
                "query_strategy": SOCIAL_STRATEGY,
                "query_plan_schema": "social_query_plan.v1",
                "default_executes_platform": False,
            }
        )
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
                routes.append({"channel": "xhs", "mode": "visible_search", "skill": "skills/xhs-visible-research", "input_count": len(queries), "uses_declared_task_scope": True, "requires_shared_gui_serialization": True, "searcher_mode": request.get("searcher_mode") or "researcher", "query_strategy": SOCIAL_STRATEGY, "query_plan_schema": "social_query_plan.v1", "default_executes_platform": False})
        elif channel in {"public_web", "official_document"}:
            cfg = request.get("public_web") or {}
            inputs = (cfg.get("known_urls") or []) + (cfg.get("queries") or [])
            if not inputs:
                errors.append(f"{channel} requires known_urls or queries")
            else:
                routes.append({"channel": channel, "mode": "official_source_resolution", "skill": "skills/public-web-official-resolver", "input_count": len(inputs), "uses_declared_task_scope": True, "requires_shared_gui_serialization": False, "default_executes_platform": False})
        elif channel == "map_gis":
            cfg = request.get("map_gis") or {}
            if not cfg.get("project_anchor"):
                errors.append("map_gis requires project_anchor")
            else:
                routes.append({"channel": "map_gis", "mode": "spatial_evidence", "skill": "skills/map-spatial-evidence", "input_count": 1 + len(cfg.get("pois") or []), "uses_declared_task_scope": True, "requires_shared_gui_serialization": False, "default_executes_platform": False})

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
