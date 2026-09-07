#!/usr/bin/env python3
"""Build the deterministic public RC manifest after the offline harness passes."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugins/public-info-research-kit"
OUTPUT = REPO / "PUBLIC_BETA_MANIFEST.json"
EXCLUDED_NAMES = {"PUBLIC_BETA_MANIFEST.json", ".DS_Store"}
EXCLUDED_PARTS = {".git", "__pycache__"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
SENSITIVE_NAMES = {".env", "cookies.sqlite", "credentials.json", "login data", "storage_state.json"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def release_files() -> list[Path]:
    files = []
    for path in REPO.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(REPO)
        if path.name in EXCLUDED_NAMES or any(part in EXCLUDED_PARTS for part in relative.parts) or path.suffix in EXCLUDED_SUFFIXES:
            continue
        if path.name.casefold() in SENSITIVE_NAMES:
            raise RuntimeError(f"sensitive artifact is not allowed: {relative.as_posix()}")
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(REPO).as_posix())


def run_harness() -> dict:
    command = [sys.executable, str(PLUGIN / "tests/run_release_harness.py")]
    completed = subprocess.run(command, cwd=PLUGIN, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError("release harness failed: " + (completed.stderr or completed.stdout)[-2000:])
    report = json.loads(completed.stdout)
    if report.get("status") != "pass":
        raise RuntimeError("release harness did not pass")
    return report


def main() -> int:
    plugin = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    version = plugin["version"]
    harness = run_harness()
    skills = sorted(path.parent.name for path in (PLUGIN / "skills").glob("*/SKILL.md"))
    files = release_files()
    manifest = {
        "schema": "public_info_self_service_release_manifest.v3",
        "version": version,
        "status": "unreleased_candidate_revision",
        "base_release_tag": "v0.8.0-rc.3",
        "candidate_revision": "2026-09-07-channel-alignment",
        "distribution_model": "public_repository_direct_use_without_maintainer_authorization",
        "license": "MIT",
        "repository": "xiem-public-info/public-info-research-kit",
        "previous_stable_version": "0.7.0",
        "private_source_commit": "acf90a64ef91eb096d6fc4be35b876cd44f4da18",
        "public_package_source": "curated_snapshot_without_private_repository_history_or_runtime_state",
        "skill_count": len(skills),
        "skills": skills,
        "quality_contracts": [
            "channel_capability_profiles",
            "D235_semantic_query_strategy",
            "D292_research_orchestration",
            "D291_spatial_coordinate_evidence_v2",
            "D293_task_driven_retrieval_authority",
            "wechat_ai_search_task_gate",
            "D237_D240_D241_adaptive_sufficiency",
            "evidence_consumer_rejection",
            "per_machine_smoke_separation",
            "residential_v0_2_interoperability_lock",
        ],
        "computer_use_policy": {
            "installation_owner": "end_user",
            "package_action": "remind_and_detect_only",
            "automatic_install": False,
            "automatic_enable": False,
            "automatic_permission_change": False,
            "login_operation": False,
        },
        "channel_routes": {
            "wechat": "WECHAT-LITE-DIRECT-CU-V1 / stable route / per-machine smoke required",
            "wechat_ai_search": "WECHAT-AI-SEARCH-SURFACE-V1 / task_driven_retrieval_ready / task authority inherited / installation live validation separate",
            "xhs": "XHS-SEARCH-V1 / visible normal Chrome / per-machine smoke required",
            "public_web": "static public web and official source resolver",
            "public_dynamic_page": "controlled runtime capture / source-specific verification",
            "official_document": "HTML, native PDF, scanned or mixed PDF, necessary-page OCR",
            "rss_feed": "discovery_only / original source required",
            "map_spatial": "spatial_coordinate_evidence.v2 / caller-owned set / single centerpoint / downstream rendering / conditional OSM attribution",
        },
        "excluded_capabilities": [
            "institutional_databases_and_dedicated_report_operations",
            "land_database_and_land_specific_consumers",
            "mingyuan_weekly_runtime_service",
            "MediaCrawler_or_CDP_or_XHS_Searcher",
            "WeChat_V2_or_Pad_or_AX",
            "W33_runtime_state_or_real_query_learning_records",
            "week33_internal_wakeup_and_experiment_state",
            "real_query_learning_records_and_business_samples",
            "credentials_cookies_tokens_profiles_or_runtime_state",
        ],
        "validation": {
            "harness_schema": harness["schema"],
            "test_runner_count": harness["test_runner_count"],
            "fixture_case_count": harness["fixture_case_count"],
            "fixture_failure_count": harness["fixture_failure_count"],
            "golden_task_fixture_count": harness["golden_task_fixture_count"],
            "negative_fixture_file_count": harness["negative_fixture_file_count"],
            "release_tree_scan_passed": harness["release_tree_scan"]["passed"],
            "offline_only": True,
            "real_gui_validated": False,
            "business_acceptance_validated": False,
            "second_user_uat_validated": False,
        },
        "interop": {
            "manifest": "plugins/public-info-research-kit/schemas/public_interop_manifest.v1.json",
            "producer_schema_sha256": harness["interface_sha256_raw_file_bytes"]["schemas/public_evidence_envelope.v1.json"],
            "residential_bridge_lock": "plugins/public-info-research-kit/bridges/residential-v0.2/consumer-contract-lock.v0.2.json",
            "candidate_conformance_passed": True,
            "both_packages_published": False,
        },
        "files": [
            {
                "path": path.relative_to(REPO).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in files
        ],
    }
    OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "version": version, "file_count": len(files), "fixture_case_count": harness["fixture_case_count"], "output": OUTPUT.name}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
