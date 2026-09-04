#!/usr/bin/env python3
"""Verify every public route declares the maintained capability profile and GUI gate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/route_task.py"
SPEC = importlib.util.spec_from_file_location("route_task", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def main() -> int:
    request = {
        "schema": "public_info_research_request.v1",
        "task_id": "fixture-all-routes",
        "subject": "某公开研究对象",
        "business_question": "哪些公开证据支持或反驳当前业务判断",
        "requested_evidence": ["原始来源", "软证据", "反例", "缺口"],
        "channel_scope": ["wechat", "xhs", "public_web", "public_dynamic_page", "official_document", "rss_feed", "map_gis"],
        "usage_boundary": "内部研究候选",
        "stop_condition": "完成约定覆盖或触发停止线",
        "searcher_mode": "researcher",
        "wechat": {
            "ai_queries": ["某对象 身份与信息供给"],
            "queries": ["某对象 交付后"],
        },
        "xhs": {"queries": ["某对象 入住体验"]},
        "public_web": {"known_urls": ["https://example.com/source"]},
        "public_dynamic_page": {"known_urls": ["https://example.com/dynamic"]},
        "official_document": {"known_urls": ["https://example.com/document.pdf"]},
        "rss_feed": {"feed_urls": ["https://example.com/feed.xml"]},
        "map_gis": {"project_anchor": "某项目", "pois": ["某公共设施"]},
    }
    result = MODULE.build_plan(request)
    cases = []
    for route in result["routes"]:
        profile = ROOT / route.get("capability_profile", "")
        profile_ok = profile.is_file()
        profile_data = json.loads(profile.read_text(encoding="utf-8")) if profile_ok else {}
        profile_contract_ok = (
            profile_data.get("schema") == "channel_capability_profile.v1"
            and profile_data.get("execution_owner") == "installed_public_info_research_kit"
            and isinstance(profile_data.get("good_at"), list)
            and bool(profile_data.get("good_at"))
            and isinstance(profile_data.get("not_good_at"), list)
            and bool(profile_data.get("not_good_at"))
            and isinstance(profile_data.get("golden_method"), list)
            and bool(profile_data.get("golden_method"))
            and isinstance(profile_data.get("required_validators"), list)
            and bool(profile_data.get("required_validators"))
        )
        gui_ok = True
        channel_invariants_ok = True
        if route.get("requires_shared_gui_serialization"):
            policy = profile_data.get("package_policy") or {}
            gui_ok = (
                route.get("portable_preflight_schema") == "portable_channel_request.v1"
                and route.get("portable_preflight_tool") == "tools/check_portable_channel_preflight.py"
                and route.get("computer_use_installation_policy")
                == "end_user_installs_and_authorizes_package_reminds_and_detects_only"
                and policy.get("install_or_enable_computer_use") is False
                and policy.get("grant_system_permissions") is False
                and policy.get("operate_login") is False
                and policy.get("remind_and_detect_only") is True
            )
        forbidden = " ".join(profile_data.get("forbidden_routes") or []).casefold()
        not_good = " ".join(profile_data.get("not_good_at") or []).casefold()
        if route["channel"] == "wechat":
            channel_invariants_ok = all(
                token in forbidden
                for token in ("wechat_v2", "query_pad", "native_ax", "dom_or_playwright", "fixed_coordinates", "automatic_same_query_fallback")
            )
            if route.get("surface_id") == "wechat_ai_search":
                channel_invariants_ok = channel_invariants_ok and all(
                    (
                        route.get("mode") == "aggregate_ai_task_retrieval",
                        route.get("gate_request_schema") == "wechat_ai_search_gate_request.v1",
                        route.get("gate_tool") == "tools/check_wechat_ai_search_gate_preflight.py",
                        route.get("research_orchestration_schema") == "d292_research_orchestration.v1",
                        route.get("status") == "task_driven_retrieval_ready_not_live_revalidated",
                        route.get("execution_authorized") is False,
                        route.get("real_gui_validated") is False,
                        route.get("original_source_backread_required") is True,
                        route.get("default_executes_platform") is False,
                    )
                )
        elif route["channel"] == "xhs":
            channel_invariants_ok = all(
                token in forbidden
                for token in ("playwright_or_cdp", "dom_snapshot", "isolated_or_copied_profile", "mediacrawler")
            )
        elif route["channel"] == "map_gis":
            channel_invariants_ok = all(token in not_good for token in ("卫星", "批量下载", "显示好看"))
            channel_invariants_ok = channel_invariants_ok and all((
                route.get("output_contract") == profile_data.get("contract") == "spatial_coordinate_evidence.v2",
                route.get("object_set_owner") == profile_data.get("object_set_owner") == "downstream_consumer",
                route.get("project_location_model") == profile_data.get("project_location_model") == "single_map_marker_centerpoint",
                route.get("rendering_owner") == profile_data.get("rendering_owner") == "downstream_consumer",
                route.get("display_validation_required_for_coordinate_package") is False,
                (ROOT / route["validator"]).is_file(),
                "tools/validate_osm_display_receipt.py" not in profile_data["required_validators"],
            ))
        cases.append(
            {
                "channel": route["channel"],
                "mode": route["mode"],
                "profile_exists": profile_ok,
                "profile_contract_ok": profile_contract_ok,
                "gui_contract_ok": gui_ok,
                "channel_invariants_ok": channel_invariants_ok,
                "passed": profile_ok and profile_contract_ok and gui_ok and channel_invariants_ok,
            }
        )
    report = {
        "schema": "route_capability_profile_fixture_report.v1",
        "status": "pass" if result["status"] == "pass" and all(row["passed"] for row in cases) else "fail",
        "route_count": len(cases),
        "failure_count": sum(not row["passed"] for row in cases),
        "cases": cases,
        "platform_opened": False,
        "network_accessed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
