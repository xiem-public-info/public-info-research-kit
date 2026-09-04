#!/usr/bin/env python3
"""Run the dependency-light public release contract, fixture and residue harness."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
TESTS = (
    "run_task_driven_retrieval.py",
    "run_route_capability_profiles.py",
    "run_portable_channel_preflight.py",
    "run_wechat_ai_search_gate_preflight.py",
    "run_social_query_plan.py",
    "run_d292_research_orchestration.py",
    "run_adaptive_query_sufficiency.py",
    "run_public_evidence_contract.py",
    "run_official_source_fixture.py",
    "run_xhs_evidence_security.py",
    "run_osm_display_receipt.py",
    "run_spatial_coordinate_evidence_v2.py",
    "run_doctor_policy.py",
    "run_per_machine_smoke_contract.py",
    "run_residential_bridge_lock.py",
)
EXPECTED_SKILLS = {
    "map-spatial-evidence",
    "public-evidence-delivery",
    "public-info-intake-router",
    "public-web-official-resolver",
    "wechat-known-url-reader",
    "wechat-public-research",
    "xhs-visible-research",
}
FORBIDDEN_ARTIFACT_PATH_TOKENS = {
    "article_gui_execution_receipt",
    "wechat_query_pad",
    "accessible_text_input",
    "week33",
    "learning_records",
    "mingyuan_weekly",
}
FORBIDDEN_BASENAMES = {
    ".env",
    "cookies.sqlite",
    "credentials.json",
    "login data",
    "storage_state.json",
}
FORBIDDEN_PRIVATE_CONTENT = {
    "/Users/" + "xieming/",
    "file:///Users/" + "xieming/",
    "repository_" + "local_main",
    "week" + "33_rule_optimization_wakeup",
    "ue-opportunity-" + "system-main",
}
TEXT_SUFFIXES = {".md", ".json", ".py", ".txt", ".toml", ".yaml", ".yml"}
INTERFACE_FILES = (
    "schemas/public_evidence_envelope.v1.json",
    "schemas/adaptive_query_sufficiency_contract.v1.json",
    "schemas/portable_channel_request.v1.json",
    "schemas/wechat_ai_search_gate_request.v1.json",
    "schemas/d292_research_orchestration.v1.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_fixture(filename: str) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tests" / filename)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        report = {
            "status": "fail",
            "case_count": 0,
            "failure_count": 1,
            "parse_error": completed.stdout[-1000:],
        }
    return {
        "test": filename,
        "returncode": completed.returncode,
        "status": report.get("status"),
        "case_count": int(report.get("case_count", report.get("route_count", 0))),
        "failure_count": int(report.get("failure_count", 0)),
        "network_accessed": report.get("network_accessed", False),
        "platform_opened": report.get("platform_opened", False),
        "external_write_executed": report.get("external_write_executed", False),
        "passed": completed.returncode == 0 and report.get("status") == "pass",
        "stderr": completed.stderr[-1000:] if completed.stderr else "",
    }


def scan_release_tree() -> dict[str, Any]:
    artifact_findings: list[str] = []
    sensitive_findings: list[str] = []
    private_content_findings: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(REPO_ROOT).as_posix()
        lowered_path = relative.casefold()
        if any(token in lowered_path for token in FORBIDDEN_ARTIFACT_PATH_TOKENS):
            artifact_findings.append(relative)
        if path.name.casefold() in FORBIDDEN_BASENAMES:
            sensitive_findings.append(relative)
        if path.suffix.casefold() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
            matched = sorted(token for token in FORBIDDEN_PRIVATE_CONTENT if token in text)
            if matched:
                private_content_findings.append(f"{relative}:{','.join(matched)}")
    return {
        "forbidden_artifact_paths": sorted(artifact_findings),
        "sensitive_artifact_paths": sorted(sensitive_findings),
        "private_content_findings": sorted(private_content_findings),
        "passed": not artifact_findings and not sensitive_findings and not private_content_findings,
    }


def check_skill_inventory() -> dict[str, Any]:
    skills_root = ROOT / "skills"
    actual = {path.parent.name for path in skills_root.glob("*/SKILL.md")}
    invalid: list[str] = []
    for skill_name in sorted(actual):
        text = (skills_root / skill_name / "SKILL.md").read_text(encoding="utf-8")
        if not text.startswith("---\n") or f"name: {skill_name}\n" not in text or "\ndescription:" not in text:
            invalid.append(skill_name)
    return {
        "expected": sorted(EXPECTED_SKILLS),
        "actual": sorted(actual),
        "invalid_frontmatter": invalid,
        "passed": actual == EXPECTED_SKILLS and not invalid,
    }


def check_interop_manifest(interface_hashes: dict[str, str]) -> dict[str, Any]:
    path = ROOT / "schemas/public_interop_manifest.v1.json"
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    producer = manifest.get("producer_interface") if isinstance(manifest, dict) else None
    producer = producer if isinstance(producer, dict) else {}
    schema_path = producer.get("path")
    target = ROOT / schema_path if isinstance(schema_path, str) else None
    target_schema = json.loads(target.read_text(encoding="utf-8")) if target and target.is_file() else {}
    expected_hash = interface_hashes.get(schema_path or "")
    preserved = manifest.get("fields_preserved_end_to_end") or []
    passed = (
        manifest.get("schema") == "public_interop_manifest.v1"
        and target is not None
        and target.is_file()
        and producer.get("$id") == target_schema.get("$id") == "public_evidence_envelope.v1"
        and producer.get("sha256") == expected_hash
        and set(producer.get("upstream_statuses") or []) == {"fulfilled", "partial", "gap", "stopped"}
        and producer.get("empty_conflicts_and_gaps_representation") == "empty_array"
        and producer.get("downstream_acceptance_in_upstream_envelope") == "not_assessed_only"
        and {"request_id", "project_id", "negative_hits", "conflicts", "gaps", "stop_reason"}.issubset(set(preserved))
    )
    return {
        "manifest_path": "schemas/public_interop_manifest.v1.json",
        "producer_schema_path": schema_path,
        "producer_schema_id": producer.get("$id"),
        "declared_sha256": producer.get("sha256"),
        "actual_sha256": expected_hash,
        "passed": passed,
    }


def main() -> int:
    fixture_reports = [run_fixture(filename) for filename in TESTS]
    tree_scan = scan_release_tree()
    skills = check_skill_inventory()
    golden_count = len(list((ROOT / "tests/fixtures/golden-tasks").glob("*.json")))
    negative_count = len(list((ROOT / "tests/fixtures/negative-cases").glob("*.json")))
    fixture_inventory_passed = 3 <= golden_count <= 5 and negative_count >= 4
    interface_hashes = {
        relative: sha256_file(ROOT / relative)
        for relative in INTERFACE_FILES
    }
    interop_manifest = check_interop_manifest(interface_hashes)
    all_passed = (
        all(report["passed"] for report in fixture_reports)
        and tree_scan["passed"]
        and skills["passed"]
        and fixture_inventory_passed
        and interop_manifest["passed"]
    )
    report = {
        "schema": "public_release_harness_report.v1",
        "status": "pass" if all_passed else "fail",
        "test_runner_count": len(fixture_reports),
        "fixture_case_count": sum(row["case_count"] for row in fixture_reports),
        "fixture_failure_count": sum(row["failure_count"] for row in fixture_reports),
        "fixture_reports": fixture_reports,
        "golden_task_fixture_count": golden_count,
        "negative_fixture_file_count": negative_count,
        "fixture_inventory_passed": fixture_inventory_passed,
        "skill_inventory": skills,
        "release_tree_scan": tree_scan,
        "interface_sha256_raw_file_bytes": interface_hashes,
        "interop_manifest": interop_manifest,
        "hash_command": "shasum -a 256 <schema-file>",
        "offline_only": True,
        "network_accessed": False,
        "platform_opened": False,
        "external_write_executed": False,
        "real_gui_validated": False,
        "business_acceptance_validated": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
